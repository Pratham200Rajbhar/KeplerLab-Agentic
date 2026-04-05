"""Hybrid retriever — dense + lexical → reciprocal rank fusion."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.db.prisma_client import prisma
from app.services.notebook_corpus.enums import RetrievalMode
from app.services.notebook_corpus.indexing import embedder, vector_store
from app.services.notebook_corpus.indexing.lexical_store import LexicalIndex
from app.services.notebook_corpus.schemas import CitationAnchor, GroundedContext

logger = logging.getLogger(__name__)


async def retrieve_hybrid(
    notebook_id: str,
    user_id: str,
    query: str,
    *,
    dense_k: int | None = None,
    lexical_k: int | None = None,
    final_k: int | None = None,
) -> GroundedContext:
    """
    Hybrid retrieval: dense vector search + BM25 lexical → RRF fusion.
    """
    dk = dense_k or settings.DENSE_K
    lk = lexical_k or settings.LEXICAL_K
    fk = final_k or settings.FINAL_K

    # 1. Dense retrieval via ChromaDB
    query_embedding = await embedder.embed_query(query)
    dense_results = await vector_store.query_similar(
        notebook_id=notebook_id,
        query_embedding=query_embedding,
        n_results=dk,
    )

    # 2. Lexical retrieval via BM25
    lexical_index = await _build_lexical_index(notebook_id, user_id)
    lexical_results = lexical_index.search(query, top_k=lk)

    # 3. Reciprocal Rank Fusion
    fused = _reciprocal_rank_fusion(dense_results, lexical_results, k=60)

    # 4. Take top-K
    top_items = fused[:fk]

    if not top_items:
        return GroundedContext(
            context_text="",
            retrieval_mode=RetrievalMode.INDEXED_RETRIEVAL,
            citations=[],
            total_tokens=0,
            sources_used=0,
            chunks_used=0,
        )

    # 5. Build context
    blocks: List[str] = []
    citations: List[CitationAnchor] = []
    seen_sources: set[str] = set()
    total_tokens = 0

    for item in top_items:
        text = item["text"]
        source_id = item.get("source_id", "")
        section_title = item.get("section_title", "")
        page_number = item.get("page_number")
        title = item.get("source_title", source_id[:8])

        # Annotate with citation
        label_parts = [f"SOURCE: {title}"]
        if section_title:
            label_parts.append(section_title)
        if page_number:
            label_parts.append(f"Page {page_number}")
        label = " | ".join(label_parts)

        blocks.append(f"[{label}]\n{text}")
        total_tokens += len(text) // 4

        if source_id not in seen_sources:
            seen_sources.add(source_id)
            citations.append(CitationAnchor(
                source_id=source_id,
                title=title,
                section_title=section_title,
                page_number=page_number,
            ))

    context_text = "\n\n---\n\n".join(blocks)

    return GroundedContext(
        context_text=context_text,
        retrieval_mode=RetrievalMode.INDEXED_RETRIEVAL,
        citations=citations,
        total_tokens=total_tokens,
        sources_used=len(seen_sources),
        chunks_used=len(top_items),
    )


def _reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    lexical_results: List[tuple],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) to merge dense and lexical results.
    RRF score = sum(1 / (k + rank)) for each result list containing the item.
    """
    rrf_scores: Dict[str, float] = {}
    item_data: Dict[str, Dict[str, Any]] = {}

    # Dense results
    for rank, result in enumerate(dense_results):
        doc_id = result["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        if doc_id not in item_data:
            metadata = result.get("metadata", {})
            item_data[doc_id] = {
                "text": result.get("document", ""),
                "source_id": metadata.get("source_id", ""),
                "section_title": metadata.get("section_title", ""),
                "page_number": metadata.get("page_number"),
                "source_title": metadata.get("source_title", ""),
            }

    # Lexical results
    for rank, (doc_id, score, text) in enumerate(lexical_results):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        if doc_id not in item_data:
            item_data[doc_id] = {"text": text, "source_id": "", "section_title": "", "page_number": None}

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    return [
        {"id": doc_id, "rrf_score": rrf_scores[doc_id], **item_data.get(doc_id, {"text": ""})}
        for doc_id in sorted_ids
    ]


async def _build_lexical_index(notebook_id: str, user_id: str) -> LexicalIndex:
    """Build a BM25 lexical index from the notebook's chunks."""
    index = LexicalIndex()

    chunks = await prisma.sourcechunk.find_many(
        where={
            "source": {
                "notebookId": notebook_id,
                "userId": user_id,
                "status": "READY",
            },
        },
        take=settings.LEXICAL_POOL,
        order={"createdAt": "desc"},
    )

    for chunk in chunks:
        doc_id = chunk.chromaId or f"{chunk.sourceId}_chunk_{chunk.chunkIndex}"
        index.add_document(doc_id, chunk.text)

    return index
