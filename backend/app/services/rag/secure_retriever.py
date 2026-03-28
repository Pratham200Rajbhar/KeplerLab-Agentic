from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from typing import List, Optional, Dict

import numpy as np

from app.db.chroma import get_collection
from app.services.rag.reranker import rerank_chunks
from app.services.rag.context_formatter import format_context_with_citations
from app.services.rag.hybrid_retrieval import (
    adaptive_retrieval_k,
    bm25_like_scores,
    reciprocal_rank_fusion,
    rewrite_query_variants,
)
from app.core.config import settings

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.retrieval")


DEFAULT_PER_MATERIAL_K = 10
CROSS_DOC_PER_MATERIAL_K = 15
MIN_CHUNKS_PER_MATERIAL = 1
MAX_CHUNKS_PER_MATERIAL = 3
CROSS_DOC_FINAL_K = 10
DEFAULT_FINAL_K = 10

CROSS_DOC_KEYWORDS = {
    'compare', 'comparison', 'difference', 'differences', 'contrast',
    'vs', 'versus', 'similarities', 'distinguish', 'distinguish between',
    'how do', 'what is the difference', 'compare and contrast'
}

class TenantIsolationError(Exception):
    pass

def _build_where(
    user_id: Optional[str],
    material_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
) -> Optional[dict]:
    clauses: List[dict] = []

    if user_id:
        clauses.append({"user_id": user_id})

    if notebook_id:
        clauses.append({"notebook_id": notebook_id})

    if material_ids and len(material_ids) > 1:
        clauses.append({"material_id": {"$in": material_ids}})
    elif material_ids and len(material_ids) == 1:
        clauses.append({"material_id": material_ids[0]})
    elif material_id:
        clauses.append({"material_id": material_id})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}

def _is_cross_document_query(query: str) -> bool:
    query_lower = query.lower()

    keyword_patterns = [
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bdifferences?\b",
        r"\bcontrast\b",
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\bsimilarities\b",
        r"\bdistinguish(?:\s+between)?\b",
        r"\bcompare\s+and\s+contrast\b",
        r"\bwhat\s+is\s+the\s+difference\b",
    ]

    if any(re.search(pat, query_lower) for pat in keyword_patterns):
        logger.info(f"Cross-document query detected: {query[:60]}...")
        return True
    
    if re.search(r'\b\w+\s+vs\.?\s+\w+\b', query_lower):
        logger.info(f"Cross-document query detected (vs pattern): {query[:60]}...")
        return True
    
    return False

def _ensure_source_diversity(
    chunks_with_metadata: List[Dict],
    min_per_material: int = MIN_CHUNKS_PER_MATERIAL,
    max_per_material: int = MAX_CHUNKS_PER_MATERIAL,
) -> List[Dict]:
    by_material = defaultdict(list)
    for chunk in chunks_with_metadata:
        material_id = chunk.get('material_id', 'unknown')
        by_material[material_id].append(chunk)
    
    if len(by_material) <= 1:
        return chunks_with_metadata[:settings.FINAL_K]
    
    logger.info(f"Balancing {len(chunks_with_metadata)} chunks across {len(by_material)} materials")
    
    balanced = []
    for material_id, chunks in by_material.items():
        balanced.extend(chunks[:min_per_material])
    
    remaining_slots = settings.FINAL_K - len(balanced)
    if remaining_slots > 0:
        remaining = []
        for material_id, chunks in by_material.items():
            remaining.extend(chunks[min_per_material:max_per_material])
        
        remaining.sort(key=lambda x: x.get('score', 0), reverse=True)
        balanced.extend(remaining[:remaining_slots])
    
    balanced.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    logger.info(
        f"Source diversity: {len(balanced)} chunks from {len(by_material)} materials "
        f"(min={min_per_material}, max={max_per_material})"
    )
    
    return balanced[:settings.FINAL_K]

def secure_similarity_search(
    user_id: str,
    query: str,
    k: int = 5,
    *,
    material_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
) -> List[str]:

    if not user_id or not user_id.strip():
        security_logger.warning(
            "Retrieval attempted WITHOUT user_id | query=%r", query[:120]
        )
        raise TenantIsolationError(
            "user_id is required for tenant-isolated retrieval"
        )

    where = _build_where(
        user_id=user_id,
        material_id=material_id,
        material_ids=material_ids,
        notebook_id=notebook_id,
    )

    if where is None or not _filter_contains_user_id(where, user_id):
        security_logger.warning(
            "Filter missing user_id clause | user_id=%s where=%s", user_id, where
        )
        raise TenantIsolationError(
            "Constructed filter does not contain the required user_id clause"
        )

    collection = get_collection()

    total_in_collection = collection.count()
    if total_in_collection == 0:
        logger.warning("ChromaDB collection is empty — no results possible")
        return []
    safe_k = max(1, min(k, total_in_collection))

    results = collection.query(query_texts=[query], n_results=safe_k, where=where)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    _validate_result_ownership(user_id, documents, metadatas, query)

    return documents

def _apply_mmr(
    query_embedding: List[float],
    documents: List[str],
    embeddings: List[List[float]],
    lambda_param: float,
    k: int,
) -> List[int]:
    if len(documents) <= k:
        return list(range(len(documents)))
    
    if len(embeddings) == 0 or not query_embedding:
        return list(range(min(k, len(documents))))
    
    try:
        query_vec = np.array(query_embedding, dtype=np.float32)
        doc_vecs = np.array(embeddings, dtype=np.float32)
        
        if query_vec.ndim != 1 or doc_vecs.ndim != 2:
            logger.warning(f"MMR: Invalid array shapes - query: {query_vec.shape}, docs: {doc_vecs.shape}")
            return list(range(min(k, len(documents))))
            
        if query_vec.shape[0] != doc_vecs.shape[1]:
            logger.warning(f"MMR: Dimension mismatch - query: {query_vec.shape[0]}, docs: {doc_vecs.shape[1]}")
            return list(range(min(k, len(documents))))
        
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm
        
        doc_norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        doc_norms = np.where(doc_norms == 0, 1, doc_norms)
        doc_vecs = doc_vecs / doc_norms
        
        query_similarities = np.dot(doc_vecs, query_vec)
        
    except Exception as e:
        logger.warning(f"MMR array operations failed: {e}")
        return list(range(min(k, len(documents))))
    
    selected_indices = []
    remaining_indices = list(range(len(documents)))
    
    first_idx = int(np.argmax(query_similarities))
    selected_indices.append(first_idx)
    remaining_indices.remove(first_idx)
    
    while len(selected_indices) < k and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            relevance = query_similarities[idx]
            
            selected_vecs = doc_vecs[selected_indices]
            doc_similarities = np.dot(selected_vecs, doc_vecs[idx])
            max_sim = np.max(doc_similarities)
            
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores.append((idx, mmr_score))
        
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    return selected_indices


def _hybrid_candidates(
    collection,
    *,
    query: str,
    where: dict,
    vector_k: int,
    lexical_k: int,
    lexical_pool: int,
) -> List[Dict]:
    """Build hybrid candidates with reciprocal-rank fusion over dense + lexical retrieval."""
    ranks: Dict[str, List[int]] = {}
    item_by_id: Dict[str, Dict] = {}

    vector_docs = 0
    lexical_docs = 0

    query_variants = rewrite_query_variants(query, max_variants=2)
    for variant_idx, q in enumerate(query_variants):
        dense_results = collection.query(
            query_texts=[q],
            n_results=vector_k,
            where=where,
            include=["documents", "metadatas", "embeddings", "distances"],
        )
        d_docs = dense_results.get("documents", [[]])[0]
        d_metas = dense_results.get("metadatas", [[]])[0]
        d_ids = dense_results.get("ids", [[]])[0]
        d_embs = dense_results.get("embeddings", [[]])[0]

        for i, doc in enumerate(d_docs):
            if i >= len(d_ids) or i >= len(d_metas):
                continue
            item_id = d_ids[i]
            vector_docs += 1
            rank = i + 1 + (variant_idx * vector_k)
            ranks.setdefault(item_id, []).append(rank)
            item_by_id[item_id] = {
                "id": item_id,
                "text": doc,
                "metadata": d_metas[i],
                "embedding": d_embs[i] if i < len(d_embs) else None,
                "dense_rank": rank,
            }

    try:
        lexical_results = collection.get(
            where=where,
            include=["documents", "metadatas"],
            limit=max(lexical_k, lexical_pool),
        )
        l_docs = lexical_results.get("documents", [])
        l_metas = lexical_results.get("metadatas", [])
        l_ids = lexical_results.get("ids", [])

        lexical_scores = bm25_like_scores(query, l_docs)
        ranked_lexical = sorted(
            [(i, s) for i, s in enumerate(lexical_scores)],
            key=lambda x: x[1],
            reverse=True,
        )[:lexical_k]

        for rank, (idx, score) in enumerate(ranked_lexical, start=1):
            if idx >= len(l_ids) or idx >= len(l_metas) or idx >= len(l_docs):
                continue
            item_id = l_ids[idx]
            if not item_id:
                continue
            lexical_docs += 1
            ranks.setdefault(item_id, []).append(rank)
            if item_id not in item_by_id:
                item_by_id[item_id] = {
                    "id": item_id,
                    "text": l_docs[idx],
                    "metadata": l_metas[idx],
                    "embedding": None,
                }
            item_by_id[item_id]["lexical_rank"] = rank
            item_by_id[item_id]["lexical_score"] = float(score)
    except Exception as exc:
        logger.warning("Lexical retrieval fallback skipped: %s", exc)

    fused_scores = reciprocal_rank_fusion(ranks)
    for iid, score in fused_scores.items():
        if iid in item_by_id:
            item_by_id[iid]["fused_score"] = float(score)

    candidates = sorted(
        item_by_id.values(),
        key=lambda it: it.get("fused_score", 0.0),
        reverse=True,
    )
    logger.info(
        "Hybrid retrieval candidates: dense=%d lexical=%d fused=%d",
        vector_docs,
        lexical_docs,
        len(candidates),
    )
    return candidates


def _normalize_rank_score(score: float) -> float:
    return 1.0 / (1.0 + np.exp(-float(score)))

def secure_similarity_search_enhanced(
    user_id: str,
    query: str,
    *,
    material_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
    use_mmr: bool = True,
    use_reranker: bool = True,
    return_formatted: bool = True,
) -> str | List[str]:
    
    if not user_id or not user_id.strip():
        security_logger.warning(
            "Enhanced retrieval attempted WITHOUT user_id | query=%r", query[:120]
        )
        raise TenantIsolationError(
            "user_id is required for tenant-isolated retrieval"
        )
    
    is_cross_doc = _is_cross_document_query(query)

    mat_ids = material_ids if material_ids else ([material_id] if material_id else [])

    if len(mat_ids) > 1:
        return _retrieve_multi_source(
            user_id=user_id,
            query=query,
            material_ids=mat_ids,
            notebook_id=notebook_id,
            is_cross_doc=is_cross_doc,
            use_reranker=use_reranker,
            return_formatted=return_formatted,
        )
    
    where = _build_where(
        user_id=user_id,
        material_id=material_id,
        material_ids=material_ids,
        notebook_id=notebook_id,
    )
    
    if where is None or not _filter_contains_user_id(where, user_id):
        security_logger.warning(
            "Filter missing user_id clause | user_id=%s where=%s", user_id, where
        )
        raise TenantIsolationError(
            "Constructed filter does not contain the required user_id clause"
        )
    
    retrieval_start = time.time()
    
    collection = get_collection()
    initial_k = settings.INITIAL_VECTOR_K

    total_in_collection = collection.count()
    if total_in_collection == 0:
        logger.warning("ChromaDB collection is empty — returning no context")
        return "No relevant context found." if return_formatted else []
    safe_initial_k = adaptive_retrieval_k(query, total_in_collection, initial_k)
    safe_lexical_k = max(1, min(settings.LEXICAL_K, total_in_collection))

    candidates = _hybrid_candidates(
        collection,
        query=query,
        where=where,
        vector_k=safe_initial_k,
        lexical_k=safe_lexical_k,
        lexical_pool=settings.LEXICAL_CANDIDATE_POOL,
    )

    if not candidates:
        logger.warning("No valid documents after hybrid retrieval")
        return "No relevant context found." if return_formatted else []

    candidate_docs = [c["text"] for c in candidates]
    candidate_metas = [c.get("metadata", {}) for c in candidates]
    candidate_ids = [c["id"] for c in candidates]
    candidate_embs = [c.get("embedding") for c in candidates]

    _validate_result_ownership(
        user_id,
        candidate_docs,
        candidate_metas,
        query,
        ids=candidate_ids,
        embeddings=candidate_embs,
    )

    validated_map: Dict[str, Dict] = {}
    for i, cid in enumerate(candidate_ids):
        validated_map[cid] = {
            "text": candidate_docs[i] if i < len(candidate_docs) else "",
            "metadata": candidate_metas[i] if i < len(candidate_metas) else {},
            "embedding": candidate_embs[i] if i < len(candidate_embs) else None,
        }

    candidates = [
        {
            **c,
            "id": c["id"],
            "text": validated_map[c["id"]]["text"],
            "metadata": validated_map[c["id"]]["metadata"],
            "embedding": validated_map[c["id"]]["embedding"],
        }
        for c in candidates
        if c.get("id") in validated_map
    ]

    if not candidates:
        return "No relevant context found." if return_formatted else []

    if use_mmr and len(candidates) > settings.MMR_K:
        try:
            from app.db.chroma import _get_ef
            ef = _get_ef()
            query_embedding = [float(x) for x in ef([query])[0]]

            if query_embedding:
                mmr_docs = [c["text"] for c in candidates]
                mmr_embs: List[List[float]] = []
                for c in candidates:
                    emb = c.get("embedding")
                    if emb is None:
                        emb = [float(x) for x in ef([c["text"]])[0]]
                    mmr_embs.append(emb)
                mmr_indices = _apply_mmr(
                    query_embedding=query_embedding,
                    documents=mmr_docs,
                    embeddings=mmr_embs,
                    lambda_param=settings.MMR_LAMBDA,
                    k=min(settings.MMR_K, len(candidates)),
                )
                candidates = [candidates[i] for i in mmr_indices]
                logger.info(f"Applied MMR: {len(mmr_indices)} diverse chunks selected")
        except Exception as e:
            logger.warning(f"MMR failed, continuing without diversity: {e}")
    
    retrieval_time = time.time() - retrieval_start
    
    try:
        from app.services.performance_logger import record_retrieval_time
        record_retrieval_time(retrieval_time)
    except Exception:
        pass
    
    logger.debug(f"Retrieval (hybrid + MMR) completed in {retrieval_time:.3f}s")
    
    reranking_start = time.time()
    chunk_scores = None
    ranked_candidates = candidates
    if use_reranker and settings.USE_RERANKER:
        try:
            rerank_pool = ranked_candidates[: settings.RERANK_CANDIDATES_K]
            chunk_scores = rerank_chunks(
                query=query,
                chunks=[c["text"] for c in rerank_pool],
                top_k=settings.FINAL_K,
            )
            pos_map: Dict[str, deque] = {}
            for i, doc in enumerate([c["text"] for c in rerank_pool]):
                pos_map.setdefault(doc, deque()).append(i)

            reranked_items = []
            for chunk, score in chunk_scores:
                if chunk in pos_map and pos_map[chunk]:
                    idx = pos_map[chunk].popleft()
                    item = dict(rerank_pool[idx])
                    item["score"] = float(score)
                    reranked_items.append(item)

            ranked_candidates = reranked_items
            logger.info("Reranked to top %d chunks", len(ranked_candidates))
        except Exception as e:
            logger.error("Reranking failed: %s", e)
            ranked_candidates = ranked_candidates[:settings.FINAL_K]
    else:
        ranked_candidates = ranked_candidates[:settings.FINAL_K]
    
    reranking_time = time.time() - reranking_start
    
    try:
        from app.services.performance_logger import record_reranking_time
        record_reranking_time(reranking_time)
    except Exception:
        pass
    
    logger.debug(f"Reranking completed in {reranking_time:.3f}s")

    filtered_candidates = []
    for item in ranked_candidates:
        raw_score = float(item.get("score", item.get("fused_score", 0.0)))
        norm_score = _normalize_rank_score(raw_score)
        if norm_score >= settings.MIN_SIMILARITY_SCORE:
            item["score"] = norm_score
            filtered_candidates.append(item)

    if not filtered_candidates and ranked_candidates:
        top_item = dict(ranked_candidates[0])
        top_item["score"] = max(
            settings.MIN_SIMILARITY_SCORE,
            _normalize_rank_score(float(top_item.get("score", top_item.get("fused_score", 0.0)))),
        )
        filtered_candidates = [top_item]

    logger.info(
        "retrieval_trace query=%r dense_k=%d lexical_k=%d candidates=%d reranked=%d final=%d",
        query[:140],
        safe_initial_k,
        safe_lexical_k,
        len(candidates),
        len(ranked_candidates),
        len(filtered_candidates),
    )
    try:
        from app.services.performance_logger import record_retrieval_trace
        record_retrieval_trace({
            "query": query[:140],
            "dense_k": safe_initial_k,
            "lexical_k": safe_lexical_k,
            "candidates": len(candidates),
            "reranked": len(ranked_candidates),
            "final": len(filtered_candidates),
            "agent_used": "false",
        })
    except Exception:
        pass

    if not filtered_candidates:
        return "No relevant context found." if return_formatted else []
    
    if return_formatted:
        chunks_with_metadata = []
        for i, item in enumerate(filtered_candidates[: settings.FINAL_K]):
            meta = item.get("metadata", {})
            chunk_dict = {
                "text": item.get("text", ""),
                "id": item.get("id", f"chunk_{i}"),
                "score": float(item.get("score", 0.0)),
            }
            if "section_title" in meta:
                chunk_dict["section_title"] = meta["section_title"]
            if "material_id" in meta:
                chunk_dict["material_id"] = meta["material_id"]
            if "filename" in meta:
                chunk_dict["filename"] = meta["filename"]
            
            chunks_with_metadata.append(chunk_dict)
        
        return format_context_with_citations(
            chunks_with_metadata,
            max_sources=settings.FINAL_K,
            max_tokens=settings.RAG_CONTEXT_MAX_TOKENS,
        )
    
    return [c.get("text", "") for c in filtered_candidates[: settings.FINAL_K]]

def _retrieve_multi_source(
    user_id: str,
    query: str,
    material_ids: List[str],
    notebook_id: Optional[str],
    is_cross_doc: bool,
    use_reranker: bool,
    return_formatted: bool,
) -> str | List[str]:
    per_material_k = CROSS_DOC_PER_MATERIAL_K if is_cross_doc else DEFAULT_PER_MATERIAL_K
    final_k = CROSS_DOC_FINAL_K if is_cross_doc else DEFAULT_FINAL_K
    
    logger.info(
        f"Multi-source retrieval: {len(material_ids)} materials, "
        f"per_material_k={per_material_k}, final_k={final_k}, "
        f"cross_doc={is_cross_doc}"
    )
    
    retrieval_start = time.time()
    
    collection = get_collection()
    
    where = _build_where(
        user_id=user_id,
        material_ids=material_ids,
        notebook_id=notebook_id,
    )

    if not where or not _filter_contains_user_id(where, user_id):
        security_logger.warning(
            "Multi-source filter missing user_id | user_id=%s where=%s",
            user_id, where,
        )
        raise TenantIsolationError(
            "Constructed filter does not contain the required user_id clause"
        )

    total_in_collection = collection.count()
    if total_in_collection == 0:
        logger.warning("ChromaDB collection is empty — returning no context")
        return "No relevant context found." if return_formatted else []
    batch_k = adaptive_retrieval_k(
        query,
        total_in_collection,
        per_material_k * len(material_ids),
    )

    try:
        candidates = _hybrid_candidates(
            collection,
            query=query,
            where=where,
            vector_k=batch_k,
            lexical_k=min(settings.LEXICAL_K, total_in_collection),
            lexical_pool=settings.LEXICAL_CANDIDATE_POOL,
        )
    except Exception as e:
        logger.error("Batched multi-source retrieval failed: %s", e)
        return "No relevant context found." if return_formatted else []

    if not candidates:
        logger.warning("No documents retrieved from any material")
        return "No relevant context found." if return_formatted else []

    c_docs = [c.get("text", "") for c in candidates]
    c_metas = [c.get("metadata", {}) for c in candidates]
    c_ids = [c.get("id", "") for c in candidates]
    _validate_result_ownership(user_id, c_docs, c_metas, query, ids=c_ids)
    validated_map: Dict[str, Dict] = {}
    for i, cid in enumerate(c_ids):
        validated_map[cid] = {
            "text": c_docs[i] if i < len(c_docs) else "",
            "metadata": c_metas[i] if i < len(c_metas) else {},
        }
    candidates = [
        {
            **c,
            "id": c.get("id", ""),
            "text": validated_map[c.get("id", "")]["text"],
            "metadata": validated_map[c.get("id", "")]["metadata"],
        }
        for c in candidates
        if c.get("id", "") in validated_map
    ]
    
    retrieval_time = time.time() - retrieval_start
    
    try:
        from app.services.performance_logger import record_retrieval_time
        record_retrieval_time(retrieval_time)
    except Exception:
        pass
    
    logger.info(
        "Total retrieved: %d chunks from %d materials in %.3fs",
        len(candidates),
        len(material_ids),
        retrieval_time,
    )

    reranking_start = time.time()
    chunk_scores = None
    ranked_candidates = candidates
    if use_reranker and settings.USE_RERANKER:
        try:
            rerank_pool = ranked_candidates[: max(final_k * 3, settings.RERANK_CANDIDATES_K)]
            chunk_scores = rerank_chunks(
                query=query,
                chunks=[c.get("text", "") for c in rerank_pool],
                top_k=final_k * 2,
            )

            pos_map: Dict[str, deque] = {}
            for i, doc in enumerate([c.get("text", "") for c in rerank_pool]):
                pos_map.setdefault(doc, deque()).append(i)

            reranked_items = []
            for chunk, score in chunk_scores:
                if chunk in pos_map and pos_map[chunk]:
                    idx = pos_map[chunk].popleft()
                    item = dict(rerank_pool[idx])
                    item["score"] = float(score)
                    reranked_items.append(item)

            ranked_candidates = reranked_items
            logger.info("Global reranking: top %d chunks", len(chunk_scores))
            
        except Exception as e:
            logger.error("Global reranking failed: %s", e)
            ranked_candidates = ranked_candidates[:final_k * 2]
    else:
        ranked_candidates = ranked_candidates[:final_k * 2]
    
    reranking_time = time.time() - reranking_start
    
    try:
        from app.services.performance_logger import record_reranking_time
        record_reranking_time(reranking_time)
    except Exception:
        pass
    
    logger.debug(f"Reranking completed in {reranking_time:.3f}s")
    
    chunks_with_metadata = []
    for i, item in enumerate(ranked_candidates):
        meta = item.get("metadata", {})
        score_raw = float(item.get("score", item.get("fused_score", 0.0)))
        score_norm = _normalize_rank_score(score_raw)
        if score_norm < settings.MIN_SIMILARITY_SCORE:
            continue
        chunk_dict = {
            "text": item.get("text", ""),
            "id": item.get("id", f"chunk_{i}"),
            "material_id": meta.get("material_id", "unknown"),
            "score": score_norm,
        }
        if "section_title" in meta:
            chunk_dict["section_title"] = meta["section_title"]
        if "filename" in meta:
            chunk_dict["filename"] = meta["filename"]
        
        chunks_with_metadata.append(chunk_dict)

    if not chunks_with_metadata and ranked_candidates:
        item = ranked_candidates[0]
        meta = item.get("metadata", {})
        chunks_with_metadata = [{
            "text": item.get("text", ""),
            "id": item.get("id", "chunk_0"),
            "material_id": meta.get("material_id", "unknown"),
            "section_title": meta.get("section_title"),
            "filename": meta.get("filename"),
            "score": settings.MIN_SIMILARITY_SCORE,
        }]
    
    chunks_with_metadata = _ensure_source_diversity(
        chunks_with_metadata,
        min_per_material=MIN_CHUNKS_PER_MATERIAL,
        max_per_material=MAX_CHUNKS_PER_MATERIAL,
    )

    try:
        from app.services.performance_logger import record_retrieval_trace
        record_retrieval_trace({
            "query": query[:140],
            "dense_k": batch_k,
            "lexical_k": min(settings.LEXICAL_K, total_in_collection),
            "candidates": len(candidates),
            "reranked": len(ranked_candidates),
            "final": len(chunks_with_metadata),
            "agent_used": "false",
            "multi_source": "true",
        })
    except Exception:
        pass
    
    if return_formatted:
        return format_context_with_citations(
            chunks_with_metadata,
            max_sources=final_k,
            max_tokens=settings.RAG_CONTEXT_MAX_TOKENS,
        )
    
    return [chunk["text"] for chunk in chunks_with_metadata]

def _filter_contains_user_id(where: dict, user_id: str) -> bool:
    if where.get("user_id") == user_id:
        return True
    for clause in where.get("$and", []):
        if isinstance(clause, dict) and clause.get("user_id") == user_id:
            return True
    return False

def _validate_result_ownership(
    user_id: str,
    documents: List[str],
    metadatas: List[dict],
    query: str,
    ids: list | None = None,
    embeddings: list | None = None,
) -> None:
    leaked_indices = []
    for idx, meta in enumerate(metadatas):
        doc_owner = meta.get("user_id")
        if doc_owner and doc_owner != user_id:
            security_logger.warning(
                "CROSS-TENANT LEAK BLOCKED | requested=%s got=%s "
                "doc_index=%d query=%r",
                user_id,
                doc_owner,
                idx,
                query[:120],
            )
            leaked_indices.append(idx)
    
    for idx in reversed(leaked_indices):
        documents.pop(idx)
        if idx < len(metadatas):
            metadatas.pop(idx)
        if ids is not None and idx < len(ids):
            ids.pop(idx)
        if embeddings is not None and idx < len(embeddings):
            embeddings.pop(idx)
