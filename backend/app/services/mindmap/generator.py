from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from app.prompts import get_mindmap_prompt
from app.models.mindmap_schemas import MindMapResponse
from app.services.llm_service.structured_invoker import invoke_structured
from app.services.material_service import get_material_text
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)

def generate_mindmap_sync(combined_text: str) -> dict:
    prompt = get_mindmap_prompt(combined_text)
    result = invoke_structured(prompt, MindMapResponse, max_retries=2)
    return result.model_dump()

async def generate_mindmap(
    material_ids: list[str],
    notebook_id: str,
    user_id: str,
) -> dict:
    import asyncio

    parts: list[str] = []
    for mid in material_ids:
        text = await get_material_text(str(mid), str(user_id))
        if text:
            parts.append(text)
    if not parts:
        raise ValueError("No material text found for the given material IDs")

    combined_text = "\n\n".join(parts)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, generate_mindmap_sync, combined_text)

    parent_ids = {n["parent_id"] for n in result["nodes"] if n.get("parent_id")}
    for node in result["nodes"]:
        node["has_children"] = node["id"] in parent_ids

    mindmap_id = str(uuid.uuid4())
    result["id"] = mindmap_id
    result["notebook_id"] = notebook_id
    result["material_ids"] = material_ids
    result["created_at"] = datetime.now(timezone.utc).isoformat()

    existing = await prisma.generatedcontent.find_first(
        where={
            "notebookId": notebook_id,
            "contentType": "mindmap",
            "userId": user_id,
        }
    )

    data_payload = {
        "notebookId": notebook_id,
        "userId": user_id,
        "contentType": "mindmap",
        "title": result.get("title", "Mind Map"),
        "data": json.dumps(result),
        "materialIds": material_ids,
    }

    if existing:
        await prisma.generatedcontent.update(
            where={"id": existing.id},
            data=data_payload,
        )
    else:
        await prisma.generatedcontent.create(data=data_payload)

    return result
