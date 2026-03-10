import asyncio
import logging
from typing import Optional

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)

async def create_notebook(user_id: str, name: str, description: Optional[str]):
    notebook = await prisma.notebook.create(
        data={
            "userId": user_id if isinstance(user_id, str) else str(user_id),
            "name": name,
            "description": description,
        }
    )
    logger.info(f"Created notebook: {notebook.id} for user: {user_id}")
    return notebook

async def get_user_notebooks(user_id: str, skip: int = 0, take: int = 50) -> list:
    return await prisma.notebook.find_many(
        where={"userId": user_id if isinstance(user_id, str) else str(user_id)},
        order={"createdAt": "desc"},
        skip=skip,
        take=take,
    )

async def get_notebook_by_id(notebook_id: str, user_id: str):
    return await prisma.notebook.find_first(
        where={
            "id": str(notebook_id),
            "userId": str(user_id),
        }
    )

async def update_notebook(
    notebook_id: str,
    user_id: str,
    name: Optional[str],
    description: Optional[str],
):
    notebook = await get_notebook_by_id(notebook_id, user_id)
    if not notebook:
        return None

    data = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description

    if data:
        notebook = await prisma.notebook.update(
            where={"id": str(notebook_id)},
            data=data,
        )
    return notebook

async def delete_notebook(notebook_id: str, user_id: str) -> bool:
    notebook = await get_notebook_by_id(notebook_id, user_id)
    if not notebook:
        return False

    nid = str(notebook_id)
    uid = str(user_id)

    try:
        try:
            from app.db.chroma import get_collection
            collection = get_collection()
            await asyncio.to_thread(
                collection.delete, where={"notebook_id": nid}
            )
        except Exception as chroma_exc:
            logger.warning("Failed to bulk-delete ChromaDB embeddings for notebook %s: %s", nid, chroma_exc)

        materials = await prisma.material.find_many(
            where={"notebookId": nid, "userId": uid}
        )
        for mat in materials:
            try:
                from app.services.storage_service import delete_material_text
                await asyncio.to_thread(delete_material_text, str(mat.id))
            except Exception:
                pass

        async with prisma.tx() as tx:
            await tx.responseblock.delete_many(
                where={"chatMessage": {"is": {"notebookId": nid}}}
            )
            await tx.chatmessage.delete_many(where={"notebookId": nid})
            await tx.chatsession.delete_many(where={"notebookId": nid})
            await tx.generatedcontent.delete_many(where={"notebookId": nid, "userId": uid})
            await tx.material.delete_many(where={"notebookId": nid, "userId": uid})
            await tx.notebook.delete(where={"id": nid})

    except Exception as e:
        logger.error("Failed to delete notebook %s: %s", notebook_id, e)
        return False

    logger.info("Deleted notebook and all associated data: %s", notebook_id)
    return True

async def save_notebook_content(
    notebook_id: str,
    user_id: str,
    content_type: str,
    title: Optional[str],
    data: dict,
    material_id: Optional[str],
):
    import json

    create_data: dict = {
        "notebookId": notebook_id,
        "userId": user_id,
        "contentType": content_type,
        "title": title,
        "data": json.dumps(data),
    }
    if material_id and material_id.strip():
        create_data["materialId"] = material_id

    content = await prisma.generatedcontent.create(data=create_data)
    logger.info("Saved %s content for notebook %s (id=%s)", content_type, notebook_id, content.id)
    return content

async def get_notebook_content(notebook_id: str, user_id: str) -> list:
    return await prisma.generatedcontent.find_many(
        where={"notebookId": notebook_id, "userId": user_id},
        order={"createdAt": "desc"},
    )

async def delete_notebook_content(
    notebook_id: str, user_id: str, content_id: str
) -> bool:
    content = await prisma.generatedcontent.find_first(
        where={"id": content_id, "notebookId": notebook_id, "userId": user_id}
    )
    if not content:
        return False
    await prisma.generatedcontent.delete(where={"id": content_id})
    return True

async def update_notebook_content_title(
    notebook_id: str, user_id: str, content_id: str, title: str
):
    content = await prisma.generatedcontent.find_first(
        where={"id": content_id, "notebookId": notebook_id, "userId": user_id}
    )
    if not content:
        return None
    return await prisma.generatedcontent.update(
        where={"id": content_id},
        data={"title": title},
    )
