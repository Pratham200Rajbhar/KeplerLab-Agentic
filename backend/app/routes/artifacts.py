import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/artifacts", tags=["Artifacts"])

@router.get("/{artifact_id}")
async def serve_artifact(artifact_id: str):
    record = await prisma.artifact.find_unique(where={"id": artifact_id})
    if not record:
        raise HTTPException(status_code=404, detail="Artifact not found")

    file_path = record.workspacePath
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")

    return FileResponse(
        path=file_path,
        filename=record.filename,
        media_type=record.mimeType,
    )
