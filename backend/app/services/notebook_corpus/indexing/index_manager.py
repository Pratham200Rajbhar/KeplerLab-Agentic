"""Index manager — orchestrates embedding + vector upsert + lexical build."""
from __future__ import annotations

import logging
from typing import List

from app.db.prisma_client import prisma
from app.services.notebook_corpus.chunking.chunk_models import SourceChunkData

from . import embedder, vector_store

logger = logging.getLogger(__name__)


async def index_chunks(
    source_id: str,
    notebook_id: str,
    chunks: List[SourceChunkData],
) -> int:
    """
    Index chunks: embed them, upsert to ChromaDB, persist SourceChunk records.
    Returns number of chunks indexed.
    """
    if not chunks:
        return 0

    texts = [c.text for c in chunks]

    # 1. Embed all chunks
    logger.info("Embedding %d chunks for source %s", len(chunks), source_id)
    embeddings = await embedder.embed_texts(texts)

    # 2. Build ChromaDB payloads
    ids = [f"{source_id}_chunk_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "source_id": source_id,
            "chunk_index": c.chunk_index,
            "section_title": c.section_title or "",
            "page_number": c.page_number or 0,
            "token_count": c.token_count,
        }
        for c in chunks
    ]

    # 3. Upsert to ChromaDB
    await vector_store.upsert_embeddings(
        notebook_id=notebook_id,
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    # 4. Persist SourceChunk records in DB
    for idx, chunk in enumerate(chunks):
        chroma_id = ids[idx]
        await prisma.sourcechunk.upsert(
            where={
                "sourceId_chunkIndex": {
                    "sourceId": source_id,
                    "chunkIndex": chunk.chunk_index,
                }
            },
            data={
                "create": {
                    "sourceId": source_id,
                    "chunkIndex": chunk.chunk_index,
                    "text": chunk.text,
                    "tokenCount": chunk.token_count,
                    "sectionTitle": chunk.section_title,
                    "pageNumber": chunk.page_number,
                    "chromaId": chroma_id,
                    "metadata": chunk.metadata or {},
                },
                "update": {
                    "text": chunk.text,
                    "tokenCount": chunk.token_count,
                    "sectionTitle": chunk.section_title,
                    "pageNumber": chunk.page_number,
                    "chromaId": chroma_id,
                    "metadata": chunk.metadata or {},
                },
            },
        )

    logger.info("Indexed %d chunks for source %s", len(chunks), source_id)
    return len(chunks)


async def delete_source_index(source_id: str, notebook_id: str) -> None:
    """Remove all indexed data for a source."""
    # Delete from ChromaDB
    await vector_store.delete_by_source(notebook_id, source_id)

    # Delete SourceChunk records
    await prisma.sourcechunk.delete_many(where={"sourceId": source_id})

    logger.info("Deleted index for source %s", source_id)
