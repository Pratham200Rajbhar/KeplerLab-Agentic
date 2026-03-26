import logging
import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)

async def get_notebook_by_id(notebook_id: str, user_id: str):
    return await prisma.notebook.find_first(
        where={"id": notebook_id, "userId": user_id}
    )

async def create_notebook(user_id: str, name: str, description: Optional[str] = None):
    return await prisma.notebook.create(
        data={
            "owner": {"connect": {"id": user_id}},
            "name": name,
            "description": description,
        }
    )

async def get_user_notebooks(user_id: str):
    return await prisma.notebook.find_many(
        where={"userId": user_id},
        order={"updatedAt": "desc"}
    )

async def update_notebook(
    notebook_id: str,
    user_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
):
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    
    if not update_data:
        return await get_notebook_by_id(notebook_id, user_id)

    return await prisma.notebook.update(
        where={"id": notebook_id},
        data=update_data,
    )

async def delete_notebook(notebook_id: str, user_id: str) -> bool:
    notebook = await get_notebook_by_id(notebook_id, user_id)
    if not notebook:
        return False
    await prisma.notebook.delete(where={"id": notebook_id})
    return True

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
    notebook_id: str,
    user_id: str,
    content_id: str,
    title: str,
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

async def rate_notebook_content(
    notebook_id: str,
    user_id: str,
    content_id: str,
    rating: Optional[str],
):
    content = await prisma.generatedcontent.find_first(
        where={"id": content_id, "notebookId": notebook_id, "userId": user_id}
    )
    if not content:
        return None
    return await prisma.generatedcontent.update(
        where={"id": content_id},
        data={"rating": rating},
    )

async def save_notebook_content(
    notebook_id: str,
    user_id: str,
    content_type: str,
    title: Optional[str],
    data: dict,
    material_id: Optional[str],
):
    create_data: dict = {
        "notebook": {"connect": {"id": notebook_id}},
        "user": {"connect": {"id": user_id}},
        "contentType": content_type,
        "title": title,
        "data": data if isinstance(data, str) else json.dumps(data), 
        "materialIds": [], 
    }
    if material_id and material_id.strip():
        create_data["material"] = {"connect": {"id": material_id}}

    content = await prisma.generatedcontent.create(data=create_data)
    logger.info(
        "Saved %s content for notebook %s (id=%s)",
        content_type,
        notebook_id,
        content.id,
    )
    return content

async def get_notebook_content(notebook_id: str, user_id: str) -> list:
    return await prisma.generatedcontent.find_many(
        where={"notebookId": notebook_id, "userId": user_id},
        order={"createdAt": "desc"},
    )
