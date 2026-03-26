from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.db.prisma_client import prisma
from app.services.auth import get_current_user
from app.services.notebook_service import get_notebook_by_id
from app.services.presentation.editor_service import update_presentation_content
from app.services.presentation.generator import generate_presentation_content
from app.services.presentation.pdf_exporter import export_pdf_from_html
from app.services.presentation.schemas import (
    GeneratePresentationRequest,
    PresentationResponse,
    SuggestPresentationRequest,
    SuggestPresentationResponse,
    UpdatePresentationRequest,
)
from app.services.presentation.generator import suggest_slide_count_from_context
from app.services.material_service import filter_completed_material_ids
from app.services.rag.secure_retriever import secure_similarity_search_enhanced

router = APIRouter(prefix="/presentation", tags=["presentation"])


async def _get_presentation_record(presentation_id: str, user_id: str):
    record = await prisma.generatedcontent.find_first(
        where={"id": presentation_id, "userId": user_id, "contentType": "presentation"}
    )
    if not record:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return record


@router.post("/suggest", response_model=SuggestPresentationResponse)
async def suggest_presentation_slides(
    request: SuggestPresentationRequest,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    valid_material_ids = await filter_completed_material_ids(request.material_ids, user_id)
    if not valid_material_ids:
        raise HTTPException(status_code=400, detail="No valid/completed materials selected")

    rag_context = secure_similarity_search_enhanced(
        user_id=user_id,
        query="Estimate presentation breadth and depth from selected materials",
        material_ids=valid_material_ids,
        use_mmr=True,
        use_reranker=True,
        return_formatted=True,
    )
    if not isinstance(rag_context, str):
        rag_context = ""

    return suggest_slide_count_from_context(rag_context)


@router.post("/generate", response_model=PresentationResponse)
async def generate_presentation(
    request: GeneratePresentationRequest,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    notebook = await get_notebook_by_id(request.notebook_id, user_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    try:
        return await generate_presentation_content(request, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate presentation: {exc}") from exc


@router.get("/{presentation_id}", response_model=PresentationResponse)
async def get_presentation(presentation_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user.id)
    record = await _get_presentation_record(presentation_id, user_id)

    data = record.data if isinstance(record.data, dict) else json.loads(record.data or "{}")
    return {
        "id": str(record.id),
        "notebook_id": str(record.notebookId),
        "user_id": str(record.userId),
        "content_type": record.contentType,
        "title": record.title,
        "data": data,
        "html_path": record.htmlPath,
        "ppt_path": record.pptPath,
        "material_ids": record.materialIds or [],
        "created_at": record.createdAt.isoformat() if record.createdAt else None,
    }


@router.get("/{presentation_id}/html")
async def get_presentation_html(presentation_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user.id)
    record = await _get_presentation_record(presentation_id, user_id)
    if not record.htmlPath or not os.path.exists(record.htmlPath):
        raise HTTPException(status_code=404, detail="Presentation HTML not found")
    return FileResponse(path=record.htmlPath, media_type="text/html", filename=f"{presentation_id}.html")


@router.get("/{presentation_id}/ppt")
async def get_presentation_ppt(presentation_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user.id)
    record = await _get_presentation_record(presentation_id, user_id)
    if not record.pptPath or not os.path.exists(record.pptPath):
        raise HTTPException(status_code=404, detail="Presentation PPT not found")
    return FileResponse(
        path=record.pptPath,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{presentation_id}.pptx",
    )


@router.get("/{presentation_id}/download")
async def download_presentation(
    presentation_id: str,
    format: str = Query(default="pptx"),
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    normalized_format = (format or "pptx").strip().lower()
    if normalized_format == "ppt":
        normalized_format = "pptx"

    if normalized_format not in {"pptx", "pdf", "html"}:
        raise HTTPException(status_code=400, detail="Unsupported format. Use pptx, pdf, or html")

    record = await _get_presentation_record(presentation_id, user_id)

    if normalized_format == "pptx":
        if not record.pptPath or not os.path.exists(record.pptPath):
            raise HTTPException(status_code=404, detail="Presentation PPT not found")
        return FileResponse(
            path=record.pptPath,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"{presentation_id}.pptx",
        )

    if not record.htmlPath or not os.path.exists(record.htmlPath):
        raise HTTPException(status_code=404, detail="Presentation HTML not found")

    if normalized_format == "html":
        return FileResponse(path=record.htmlPath, media_type="text/html", filename=f"{presentation_id}.html")

    html_path = Path(record.htmlPath)
    pdf_path = html_path.with_suffix(".pdf")

    # Rebuild PDF when source HTML changes, otherwise serve cached file.
    if not pdf_path.exists() or pdf_path.stat().st_mtime < html_path.stat().st_mtime:
        try:
            await export_pdf_from_html(str(html_path), str(pdf_path))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {exc}") from exc

    return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=f"{presentation_id}.pdf")


@router.post("/update", response_model=PresentationResponse)
async def update_presentation(
    request: UpdatePresentationRequest,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    try:
        return await update_presentation_content(
            presentation_id=request.presentation_id,
            user_id=user_id,
            instruction=request.instruction,
            active_slide_index=request.active_slide_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update presentation: {exc}") from exc
