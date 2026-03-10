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
from app.core.config import settings

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.retrieval")

def _expand_structured_chunks(
    documents: List[str],
    metadatas: List[dict],
) -> List[str]:
    from app.services.storage_service import load_material_text

    _MAX_EXPANDED_CHARS = 50_000
    expanded = list(documents)
    for i, meta in enumerate(metadatas):
        if str(meta.get("is_structured", "")).lower() != "true":
            continue
        material_id = meta.get("material_id")
        if not material_id:
            continue
        try:
            full_text = load_material_text(material_id)
            if full_text:
                if len(full_text) > _MAX_EXPANDED_CHARS:
                    full_text = full_text[:_MAX_EXPANDED_CHARS] + "\n\n... [truncated — full dataset too large for context]"
                    logger.warning(
                        "Structured chunk truncated to %d chars for material=%s (original: %d)",
                        _MAX_EXPANDED_CHARS, material_id, len(full_text),
                    )
                expanded[i] = full_text
                logger.info(
                    "Expanded structured chunk for material=%s (%d chars)",
                    material_id, len(full_text),
                )
        except Exception as exc:
            logger.warning(
                "Could not load full structured text for material=%s: %s",
                material_id, exc,
            )
    return expanded

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
    
    if any(keyword in query_lower for keyword in CROSS_DOC_KEYWORDS):
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
    safe_initial_k = max(1, min(initial_k, total_in_collection))

    logger.info(f"Single-source retrieval: top {safe_initial_k} chunks for query: {query[:60]}...")
    
    results = collection.query(
        query_texts=[query],
        n_results=safe_initial_k,
        where=where,
        include=['documents', 'metadatas', 'embeddings', 'distances']
    )
    
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    embeddings = results.get("embeddings", [[]])[0]
    ids = results.get("ids", [[]])[0]
    
    _validate_result_ownership(user_id, documents, metadatas, query, ids=ids, embeddings=embeddings)
    
    if not documents:
        logger.warning("No valid documents after security filtering")
        return "No relevant context found." if return_formatted else []
    
    logger.info(f"Retrieved {len(documents)} valid chunks")

    documents = _expand_structured_chunks(documents, metadatas)

    if use_mmr and len(documents) > settings.MMR_K and len(embeddings) > 0:
        try:
            from app.db.chroma import _get_ef
            ef = _get_ef()
            query_embedding = [float(x) for x in ef([query])[0]]

            if query_embedding:
                mmr_indices = _apply_mmr(
                    query_embedding=query_embedding,
                    documents=documents,
                    embeddings=embeddings,
                    lambda_param=settings.MMR_LAMBDA,
                    k=settings.MMR_K,
                )
                documents = [documents[i] for i in mmr_indices]
                metadatas = [metadatas[i] for i in mmr_indices] if metadatas else []
                ids = [ids[i] for i in mmr_indices] if ids else []
                logger.info(f"Applied MMR: {len(mmr_indices)} diverse chunks selected")
        except Exception as e:
            logger.warning(f"MMR failed, continuing without diversity: {e}")
    
    retrieval_time = time.time() - retrieval_start
    
    try:
        from app.services.performance_logger import record_retrieval_time
        record_retrieval_time(retrieval_time)
    except Exception:
        pass
    
    logger.debug(f"Retrieval (vector + MMR) completed in {retrieval_time:.3f}s")
    
    reranking_start = time.time()
    chunk_scores = None
    if use_reranker and settings.USE_RERANKER:
        try:
            chunk_scores = rerank_chunks(
                query=query,
                chunks=documents,
                top_k=settings.FINAL_K,
            )
            pos_map: Dict[str, deque] = {}
            for i, doc in enumerate(documents):
                pos_map.setdefault(doc, deque()).append(i)

            reranked_indices = []
            reranked_docs = []
            for chunk, score in chunk_scores:
                if chunk in pos_map and pos_map[chunk]:
                    reranked_indices.append(pos_map[chunk].popleft())
                    reranked_docs.append(chunk)

            metadatas = [metadatas[i] for i in reranked_indices] if metadatas else []
            ids = [ids[i] for i in reranked_indices] if ids else []
            documents = reranked_docs
            logger.info("Reranked to top %d chunks", len(documents))
        except Exception as e:
            logger.error("Reranking failed: %s", e)
            documents = documents[:settings.FINAL_K]
            metadatas = metadatas[:settings.FINAL_K] if metadatas else []
            ids = ids[:settings.FINAL_K] if ids else []
    else:
        documents = documents[:settings.FINAL_K]
        metadatas = metadatas[:settings.FINAL_K] if metadatas else []
        ids = ids[:settings.FINAL_K] if ids else []
    
    reranking_time = time.time() - reranking_start
    
    try:
        from app.services.performance_logger import record_reranking_time
        record_reranking_time(reranking_time)
    except Exception:
        pass
    
    logger.debug(f"Reranking completed in {reranking_time:.3f}s")
    
    if return_formatted:
        chunks_with_metadata = []
        for i, doc in enumerate(documents):
            chunk_dict = {
                "text": doc,
                "id": ids[i] if i < len(ids) else f"chunk_{i}",
            }
            if i < len(metadatas):
                meta = metadatas[i]
                if "section_title" in meta:
                    chunk_dict["section_title"] = meta["section_title"]
                if "material_id" in meta:
                    chunk_dict["material_id"] = meta["material_id"]
                if "filename" in meta:
                    chunk_dict["filename"] = meta["filename"]
            if chunk_scores and i < len(chunk_scores):
                chunk_dict["score"] = chunk_scores[i][1]
            
            chunks_with_metadata.append(chunk_dict)
        
        return format_context_with_citations(
            chunks_with_metadata,
            max_sources=settings.FINAL_K,
        )
    
    return documents

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
    batch_k = max(1, min(per_material_k * len(material_ids), total_in_collection))

    all_documents: List[str] = []
    all_metadatas: List[Dict] = []
    all_ids: List[str] = []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=batch_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]

        _validate_result_ownership(user_id, docs, metas, query, ids=ids)

        for i, doc in enumerate(docs):
            if doc and i < len(metas) and i < len(ids):
                all_documents.append(doc)
                all_metadatas.append(metas[i])
                all_ids.append(ids[i])

        logger.info(
            "Batched retrieval: %d chunks from %d materials in one query",
            len(all_documents), len(material_ids),
        )
    except Exception as e:
        logger.error("Batched multi-source retrieval failed: %s", e)
        return "No relevant context found." if return_formatted else []
    
    if not all_documents:
        logger.warning("No documents retrieved from any material")
        return "No relevant context found." if return_formatted else []
    
    retrieval_time = time.time() - retrieval_start
    
    try:
        from app.services.performance_logger import record_retrieval_time
        record_retrieval_time(retrieval_time)
    except Exception:
        pass
    
    logger.info(f"Total retrieved: {len(all_documents)} chunks from {len(material_ids)} materials in {retrieval_time:.3f}s")

    all_documents = _expand_structured_chunks(all_documents, all_metadatas)

    reranking_start = time.time()
    chunk_scores = None
    if use_reranker and settings.USE_RERANKER:
        try:
            chunk_scores = rerank_chunks(
                query=query,
                chunks=all_documents,
                top_k=final_k * 2,
            )

            pos_map: Dict[str, deque] = {}
            for i, doc in enumerate(all_documents):
                pos_map.setdefault(doc, deque()).append(i)

            reranked_docs = []
            reranked_indices = []
            for chunk, score in chunk_scores:
                if chunk in pos_map and pos_map[chunk]:
                    reranked_indices.append(pos_map[chunk].popleft())
                    reranked_docs.append(chunk)

            all_metadatas = [all_metadatas[i] for i in reranked_indices]
            all_ids = [all_ids[i] for i in reranked_indices]
            all_documents = reranked_docs
            logger.info("Global reranking: top %d chunks", len(chunk_scores))
            
        except Exception as e:
            logger.error("Global reranking failed: %s", e)
            all_documents = all_documents[:final_k * 2]
            all_metadatas = all_metadatas[:final_k * 2]
            all_ids = all_ids[:final_k * 2]
    else:
        all_documents = all_documents[:final_k * 2]
        all_metadatas = all_metadatas[:final_k * 2]
        all_ids = all_ids[:final_k * 2]
    
    reranking_time = time.time() - reranking_start
    
    try:
        from app.services.performance_logger import record_reranking_time
        record_reranking_time(reranking_time)
    except Exception:
        pass
    
    logger.debug(f"Reranking completed in {reranking_time:.3f}s")
    
    chunks_with_metadata = []
    for i, doc in enumerate(all_documents):
        chunk_dict = {
            "text": doc,
            "id": all_ids[i] if i < len(all_ids) else f"chunk_{i}",
            "material_id": all_metadatas[i].get("material_id", "unknown") if i < len(all_metadatas) else "unknown",
        }
        
        if i < len(all_metadatas):
            meta = all_metadatas[i]
            if "section_title" in meta:
                chunk_dict["section_title"] = meta["section_title"]
            if "filename" in meta:
                chunk_dict["filename"] = meta["filename"]
        
        if chunk_scores and i < len(chunk_scores):
            chunk_dict["score"] = chunk_scores[i][1]
        else:
            chunk_dict["score"] = 1.0
        
        chunks_with_metadata.append(chunk_dict)
    
    chunks_with_metadata = _ensure_source_diversity(
        chunks_with_metadata,
        min_per_material=MIN_CHUNKS_PER_MATERIAL,
        max_per_material=MAX_CHUNKS_PER_MATERIAL,
    )
    
    if return_formatted:
        return format_context_with_citations(
            chunks_with_metadata,
            max_sources=final_k,
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
