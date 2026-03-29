from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.prompts import get_web_search_synthesis_prompt
from app.services.llm_service.llm import get_llm, extract_chunk_content

from . import context_builder, message_store
from .router_logic import route_capability
from .schemas import Capability, ToolResult
from .streaming import (
    sse,
    sse_token,
    sse_error,
    sse_done,
    sse_blocks,
    sse_meta,
    sse_image,
)

logger = logging.getLogger(__name__)

async def run(
    message: str,
    notebook_id: str,
    user_id: str,
    session_id: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> AsyncIterator[str]:
    start_time = time.time()
    capability = route_capability(message, material_ids, intent_override)

    if capability == Capability.AGENT:
        async for event in _handle_agent(message, notebook_id, user_id, session_id, material_ids):
            yield event
        return

    if capability == Capability.IMAGE_GENERATION:
        async for event in _handle_image_generation(
            message,
            notebook_id,
            user_id,
            session_id,
            material_ids,
            start_time,
        ):
            yield event
        return

    if capability == Capability.SKILL_EXECUTION:
        async for event in _handle_skill_execution(
            message, notebook_id, user_id, session_id, material_ids, start_time,
        ):
            yield event
        return

    if capability == Capability.WEB_RESEARCH:
        async for event in _handle_research(message, notebook_id, user_id, session_id, start_time):
            yield event
        return

    if capability == Capability.CODE_EXECUTION:
        async for event in _handle_code_execution(message, notebook_id, user_id, session_id, material_ids, start_time):
            yield event
        return

    tool_result: Optional[ToolResult] = None

    if capability == Capability.RAG:
        async for item in _run_rag_tool(message, material_ids, user_id, notebook_id):
            if isinstance(item, ToolResult):
                tool_result = item
            else:
                yield item

    elif capability == Capability.WEB_SEARCH:
        async for item in _run_web_search_tool(message, user_id):
            if isinstance(item, ToolResult):
                tool_result = item
            else:
                yield item

    if capability == Capability.RAG and tool_result and tool_result.metadata.get("empty"):
        msg = (
            "I couldn't find relevant information in your selected materials "
            "for that question. Try rephrasing your query or selecting different materials."
        )
        yield sse_token(msg)
        elapsed = round(time.time() - start_time, 2)
        yield sse_meta({"intent": capability.value, "chunks_used": 0, "elapsed": elapsed})
        yield sse_done({"elapsed": elapsed})

        await _persist(notebook_id, user_id, session_id, message, msg, {"intent": capability.value, "chunks_used": 0})
        return

    history = await message_store.get_history(notebook_id, user_id, session_id)

    if capability == Capability.RAG and tool_result and tool_result.content:
        messages = context_builder.build_messages(
            user_message=message,
            history=history,
            rag_context=tool_result.content,
        )
    elif capability == Capability.WEB_SEARCH and tool_result and tool_result.content:
        synth_prompt = get_web_search_synthesis_prompt(
            search_results=tool_result.content,
            question=message,
        )
        messages = [{"role": "user", "content": synth_prompt}]
    else:
        messages = context_builder.build_messages(
            user_message=message,
            history=history,
        )

    try:
        llm = get_llm(temperature=0.3 if capability == Capability.WEB_SEARCH else None)
        full_response: List[str] = []

        prompt = _messages_to_prompt(messages)

        async for chunk in llm.astream(prompt):
            content = extract_chunk_content(chunk)
            if content:
                full_response.append(content)
                yield sse_token(content)

        answer = "".join(full_response).strip()

        if capability == Capability.RAG and tool_result:
            chunks_used = tool_result.metadata.get("chunks_used", 0)
            if chunks_used > 0:
                try:
                    from app.services.rag.citation_validator import validate_citations
                    validation = validate_citations(response=answer, num_sources=chunks_used, strict=True)
                    if not validation["is_valid"]:
                        logger.warning("Citation validation failed: %s", validation.get("error_message"))
                except Exception:
                    pass

        elapsed = round(time.time() - start_time, 2)
        meta = _build_meta(capability, tool_result, elapsed)
        yield sse_meta(meta)

        blocks, _ = await _persist(notebook_id, user_id, session_id, message, answer, meta)
        if blocks:
            yield sse_blocks(blocks)

        yield sse_done({"elapsed": elapsed, **meta})

    except Exception as exc:
        logger.error("LLM streaming failed: %s", exc)
        yield sse_error(str(exc))
        yield sse_done({"elapsed": round(time.time() - start_time, 2)})

async def _run_rag_tool(message, material_ids, user_id, notebook_id):
    from app.services.tools.rag_tool import execute
    async for item in execute(message, material_ids, user_id, notebook_id):
        yield item

async def _run_web_search_tool(message, user_id):
    from app.services.tools.web_search_tool import execute
    async for item in execute(message, user_id):
        yield item

async def _handle_research(message, notebook_id, user_id, session_id, start_time):
    from app.services.tools.research_tool import execute

    full_response: List[str] = []
    tool_result: Optional[ToolResult] = None

    async for item in execute(message, user_id, notebook_id, session_id):
        if isinstance(item, ToolResult):
            tool_result = item
        else:
            yield item

    if tool_result and tool_result.content:
        meta = {
            "intent": "WEB_RESEARCH",
            "sources_count": tool_result.metadata.get("sources_count", 0),
        }
        blocks, _ = await _persist(notebook_id, user_id, session_id, message, tool_result.content, meta)
        if blocks:
            yield sse_blocks(blocks)

    elapsed = round(time.time() - start_time, 2)
    yield sse_done({"elapsed": elapsed})

async def _handle_code_execution(message, notebook_id, user_id, session_id, material_ids, start_time):
    from app.services.tools.python_tool import execute

    tool_result: Optional[ToolResult] = None

    async for item in execute(message, material_ids, user_id, notebook_id, session_id):
        if isinstance(item, ToolResult):
            tool_result = item
        else:
            yield item

    if tool_result:
        answer = tool_result.content or "Code generated."
        code = tool_result.metadata.get("code", "")
        language = tool_result.metadata.get("language", "python")
        meta = {
            "intent": "CODE_EXECUTION",
            "original_code": code,
            "code_block": {
                "code": code,
                "language": language,
            },
            "language": language,
            "phase": tool_result.metadata.get("phase", "generated"),
        }
        await _persist(notebook_id, user_id, session_id, message, answer, meta)

    elapsed = round(time.time() - start_time, 2)
    yield sse_done({"intent": "CODE_EXECUTION", "elapsed": elapsed})

async def _handle_agent(goal, notebook_id, user_id, session_id, material_ids):
    from app.services.agent.agent_orchestrator import run_agent

    # Clean the goal for the internal agent graph, but keep original 'goal' for persistence
    clean_goal = goal.lstrip()
    if clean_goal.startswith("/agent"):
        clean_goal = clean_goal[len("/agent"):].strip()

    async for event in run_agent(
        goal=clean_goal,
        original_goal=goal, # Pass original goal for persistence
        notebook_id=notebook_id,
        user_id=user_id,
        session_id=session_id,
        material_ids=material_ids or [],
    ):
        yield event

async def _resolve_image_grounding_context(
    prompt_raw: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
) -> Dict[str, Any]:
    """Fetch compact RAG context so /image can reflect selected resources."""
    if not material_ids:
        return {"context": "", "chunks_used": 0, "grounded": False}

    try:
        from app.core.config import settings
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced

        raw_context = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query=prompt_raw,
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        if not raw_context or raw_context.strip() == "No relevant context found.":
            return {"context": "", "chunks_used": 0, "grounded": False}

        chunks_used = len(re.findall(r"\[SOURCE\s+\d+(?:\s+-\s+Material:.*?)?\]", raw_context))
        # Keep grounding concise so prompt stays within practical model limits.
        compact_context = raw_context[:3500].strip()
        return {
            "context": compact_context,
            "chunks_used": chunks_used,
            "grounded": True,
        }
    except Exception as exc:
        logger.warning("Image grounding context retrieval failed: %s", exc)
        return {"context": "", "chunks_used": 0, "grounded": False}


def _build_grounded_image_prompt(prompt_raw: str, rag_context: str) -> str:
    if not rag_context:
        return prompt_raw

    return (
        "You are generating an image from a user request and selected learning resources. "
        "Use resource facts for subject fidelity, entities, and terminology while still producing "
        "a visually compelling image.\n\n"
        f"User request:\n{prompt_raw}\n\n"
        "Selected resource context:\n"
        f"{rag_context}\n\n"
        "Instruction: Generate a single image prompt that preserves the user's intent and style, "
        "but aligns details with the resource context when relevant."
    )


async def _handle_image_generation(message, notebook_id, user_id, session_id, material_ids, start_time):
    prompt_raw = message.lstrip()[len("/image"):].strip()
    if not prompt_raw:
        yield sse_error("Please provide an image prompt after /image")
        yield sse_done({"elapsed": round(time.time() - start_time, 2)})
        return

    # Yield status immediately
    yield sse("status", {"message": "🎨 Generating image..."})

    try:
        from app.services.image_generation.gemini_service import generate_image
        import uuid
        import os
        import secrets
        from datetime import datetime, timedelta, timezone
        from app.core.config import settings
        from app.db.prisma_client import prisma

        grounding = await _resolve_image_grounding_context(
            prompt_raw=prompt_raw,
            material_ids=material_ids or [],
            user_id=user_id,
            notebook_id=notebook_id,
        )

        grounded_prompt = _build_grounded_image_prompt(
            prompt_raw=prompt_raw,
            rag_context=grounding["context"],
        )

        # Run synchronously blocking REST call via executor
        image_bytes, _generated_prompt = await asyncio.to_thread(generate_image, grounded_prompt)

        # Build DB artifact
        artifact_id = str(uuid.uuid4())
        artifacts_dir = os.path.abspath(settings.ARTIFACTS_DIR)
        os.makedirs(artifacts_dir, exist_ok=True)
        # Use JPEG extension because Gemini payload format is often JPEG, but prompt dictates PNG saving logic
        permanent_path = os.path.join(artifacts_dir, f"{artifact_id}.png")

        with open(permanent_path, "wb") as f:
            f.write(image_bytes)

        token = secrets.token_urlsafe(48)
        expiry = datetime.now(timezone.utc) + timedelta(days=3650)

        filename_short = f"{prompt_raw[:30].strip()}.png"

        record = await prisma.artifact.create(
            data={
                "id": artifact_id,
                "userId": user_id,
                "notebookId": notebook_id,
                "sessionId": session_id,
                "filename": filename_short,
                "mimeType": "image/png",
                "displayType": "image",
                "sizeBytes": len(image_bytes),
                "downloadToken": token,
                "tokenExpiry": expiry,
                "workspacePath": permanent_path,
            }
        )

        url = f"/api/artifacts/{record.id}"

        # Yield SSE event
        yield sse_image(url=url, prompt=prompt_raw, original_prompt=prompt_raw)

        # Persist standard message
        meta = {
            "intent": Capability.IMAGE_GENERATION.value, 
            "elapsed": round(time.time() - start_time, 2),
            "grounded_with_materials": grounding["grounded"],
            "chunks_used": grounding["chunks_used"],
            "images": [
                {
                    "url": url,
                    "prompt": prompt_raw,
                    "original_prompt": prompt_raw
                }
            ]
        }
        fake_assistant_response = f"Generated Image:\nPrompt: {prompt_raw}"
        await _persist(notebook_id, user_id, session_id, message, fake_assistant_response, meta)

        yield sse_done(meta)

    except Exception as exc:
        logger.error(f"Image generation failed: {exc}")
        yield sse_error("Image generation failed. Please try again later.")
        yield sse_done({"elapsed": round(time.time() - start_time, 2)})

def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    parts: List[str] = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            parts.append(content)
        elif role == "user":
            parts.append(content)
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    return "\n\n".join(parts)

def _build_meta(
    capability: Capability,
    tool_result: Optional[ToolResult],
    elapsed: float,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"intent": capability.value, "elapsed": elapsed}
    if tool_result:
        if "chunks_used" in tool_result.metadata:
            meta["chunks_used"] = tool_result.metadata["chunks_used"]
        if "sources" in tool_result.metadata:
            meta["sources"] = tool_result.metadata["sources"]
        if "queries" in tool_result.metadata:
            meta["queries_used"] = tool_result.metadata["queries"]
    return meta

async def _persist(
    notebook_id: str,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_answer: str,
    agent_meta: Dict[str, Any],
) -> tuple:
    try:
        await message_store.save_user_message(
            notebook_id, user_id, session_id, user_message, 
            agent_meta={"intent": agent_meta.get("intent")} if agent_meta else None
        )

        msg_id = await message_store.save_assistant_message(
            notebook_id, user_id, session_id, assistant_answer, agent_meta
        )

        blocks = await message_store.save_response_blocks(msg_id, assistant_answer)
        return blocks, msg_id
    except Exception as exc:
        logger.error("Persistence failed: %s", exc)
        return [], None


async def _handle_skill_execution(message, notebook_id, user_id, session_id, material_ids, start_time):
    """Handle /skills <slug> [variable=value ...] commands from chat."""
    import re as _re

    # Parse: /skills <slug> [var=val ...]
    clean = message.lstrip()
    if clean.startswith("/skills"):
        clean = clean[len("/skills"):].strip()

    parts = clean.split(None, 1)
    slug = parts[0] if parts else ""
    args_str = parts[1] if len(parts) > 1 else ""

    if not slug:
        yield sse_error("Usage: /skills <skill-name> [variable=value ...]")
        yield sse_done({"elapsed": round(time.time() - start_time, 2)})
        return

    # Parse variable=value pairs
    variables = {}
    if args_str:
        # Support both key=value and key="multi word value"
        for match in _re.finditer(r'(\w+)\s*=\s*(?:"([^"]+)"|(\S+))', args_str):
            key = match.group(1)
            value = match.group(2) or match.group(3)
            variables[key] = value

        # If no key=value found, use the whole args as user_input
        if not variables:
            variables["user_input"] = args_str
            # Also set common variable aliases
            variables["topic"] = args_str
            variables["question"] = args_str
            variables["objective"] = args_str

    from app.services.skills.skill_service import run_skill_by_slug

    final_output_parts = []

    async for event in run_skill_by_slug(
        slug=slug,
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        material_ids=material_ids or [],
        variables=variables,
    ):
        yield event

        # Collect final output for persistence
        try:
            if "skill_step_result" in event:
                import json as _json
                data_line = event.split("data: ", 1)[1].split("\n")[0]
                data = _json.loads(data_line)
                if data.get("content"):
                    final_output_parts.append(data["content"])
        except (IndexError, ValueError):
            pass

    # Persist as a chat message
    final_output = "\n\n".join(final_output_parts[-3:]) if final_output_parts else f"Skill '{slug}' executed."
    meta = {"intent": "SKILL_EXECUTION", "skill_slug": slug, "elapsed": round(time.time() - start_time, 2)}

    await _persist(notebook_id, user_id, session_id, message, final_output[:5000], meta)

