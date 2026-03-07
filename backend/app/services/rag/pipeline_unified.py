"""New RAG pipeline using unified streaming architecture.

Clean, stream-based RAG implementation using StreamManager for consistent
event handling and state management.
"""

import logging
from typing import AsyncIterator, List

from app.core.config import settings
from app.services.stream import StreamManager
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)


async def stream_rag_unified(
    query: str,
    material_ids: List[str],
    notebook_id: str,
    user_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    """Execute RAG pipeline with unified streaming.
    
    Args:
        query: User query
        material_ids: Selected material IDs
        notebook_id: Notebook ID
        user_id: User ID
        session_id: Chat session ID
        
    Yields:
        SSE formatted events
    """
    # Create stream manager
    manager = StreamManager(
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        user_message=query,
        intent="RAG",
    )
    
    try:
        # Initialize stream
        await manager.initialize()
        
        # Step 1: Retrieve context
        yield await manager.emit_step("retrieval", "running", "Searching materials...")
        
        context = ""
        chunks_used = 0
        
        if material_ids:
            from app.services.rag.secure_retriever import secure_similarity_search_enhanced
            
            context = await secure_similarity_search_enhanced(
                user_id=user_id,
                query=query,
                material_ids=material_ids,
                notebook_id=notebook_id,
                use_mmr=True,
                use_reranker=settings.USE_RERANKER,
                return_formatted=True,
            )
            
            if not context or context.strip() == "No relevant context found.":
                # No relevant context found
                msg = (
                    "I couldn't find relevant information in your selected materials "
                    "for that question. Try rephrasing your query or selecting different materials."
                )
                yield await manager.emit_token(msg)
                yield await manager.emit_step("retrieval", "done", "No relevant context found")
                
                async for event in manager.finalize({"chunks_used": 0}):
                    yield event
                return
            
            # Count chunks
            import re
            chunks_used = len(re.findall(r"\[SOURCE\s+\d+\]", context))
        
        yield await manager.emit_step("retrieval", "done", f"Found {chunks_used} relevant chunks")
        
        # Step 2: Build prompt
        yield await manager.emit_step("generation", "running", "Generating response...")
        
        from app.services.chat_v2.message_store import get_history as get_chat_history
        from app.prompts import get_chat_prompt
        
        # Get history
        raw_history = await get_chat_history(notebook_id, user_id, session_id)
        history_lines = []
        for msg in raw_history[-10:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        formatted_history = "\n".join(history_lines) if history_lines else "None"
        
        prompt = get_chat_prompt(context, formatted_history, query)
        
        # Step 3: Stream LLM response
        llm = get_llm()
        
        async for chunk in llm.astream(prompt):
            from app.services.llm_service.llm import extract_chunk_content
            content = extract_chunk_content(chunk)
            if content:
                yield await manager.emit_token(content)
        
        yield await manager.emit_step("generation", "done", "Response complete")
        
        # Step 4: Validate citations (optional)
        if chunks_used > 0:
            from app.services.rag.citation_validator import validate_citations
            answer = manager.context.full_content
            validation = validate_citations(
                response=answer,
                num_sources=chunks_used,
                strict=True,
            )
            if not validation["is_valid"]:
                logger.warning(
                    f"[rag_unified] Citation validation failed: {validation.get('error_message')}"
                )
        
        # Finalize
        async for event in manager.finalize({"chunks_used": chunks_used}):
            yield event
    
    except Exception as e:
        logger.exception(f"[rag_unified] Error: {e}")
        yield await manager.handle_error(e)
        async for event in manager.finalize():
            yield event
