from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
from functools import partial
from typing import List, Optional

from app.core.config import settings
from app.db.prisma_client import prisma
from app.core.utils import sanitize_null_bytes
from app.services.rag.embedder import embed_and_store
from app.services.text_processing.chunker import chunk_text
from app.services.storage_service import (
    save_material_text,
    load_material_text,
    delete_material_text,
    get_material_summary,
)

_STRUCTURED_SOURCE_TYPES = frozenset({"csv", "excel", "xlsx", "xls", "tsv", "ods"})

logger = logging.getLogger(__name__)

async def _emit_material_ws(user_id: str, material_id: str, status: str, **extra) -> None:
    try:
        from app.services.ws_manager import ws_manager
        payload: dict = {"type": "material_update", "material_id": material_id, "status": status}
        if extra:
            payload.update(extra)
        await ws_manager.send_to_user(user_id, payload)
    except Exception as exc:
        logger.debug("WS emit skipped (material=%s status=%s): %s", material_id, status, exc)

async def _set_status(material_id: str, status: str, user_id: Optional[str] = None, **extra) -> None:
    data: dict = {"status": status, **extra}
    try:
        await prisma.material.update(where={"id": material_id}, data=data)
    except Exception:
        logger.exception("Failed to update material %s to status=%s", material_id, status)
        return
    if user_id:
        await _emit_material_ws(user_id, material_id, status, **extra)

async def _fail_material(material_id: str, reason: str, user_id: Optional[str] = None) -> None:
    logger.error("Material %s failed: %s", material_id, reason)
    await _set_status(material_id, "failed", user_id=user_id, error=reason)

def _make_structured_summary_chunk(raw_file_path: str, fallback_text: str) -> tuple:
    import uuid
    import pandas as pd
    from pathlib import Path

    full_text = fallback_text
    summary_text = fallback_text

    try:
        if not raw_file_path:
            raise ValueError("No raw_file_path available")

        ext = Path(raw_file_path).suffix.lower()
        stem = Path(raw_file_path).stem

        if ext == ".csv":
            df = pd.read_csv(raw_file_path, encoding_errors="replace")
            sheets: dict = {"data": df}
        elif ext in (".xlsx", ".xls"):
            sheets = pd.read_excel(raw_file_path, sheet_name=None)
            if not isinstance(sheets, dict):
                sheets = {"Sheet1": sheets}
        elif ext == ".ods":
            sheets = pd.read_excel(raw_file_path, engine="odf", sheet_name=None)
            if not isinstance(sheets, dict):
                sheets = {"Sheet1": sheets}
        elif ext == ".tsv":
            df = pd.read_csv(raw_file_path, sep="\t", encoding_errors="replace")
            sheets = {"data": df}
        else:
            raise ValueError(f"Unsupported structured extension: {ext}")

        full_parts: list = []
        summary_parts: list = []
        for sheet_name, df in sheets.items():
            label = f"Sheet: {sheet_name}" if len(sheets) > 1 else stem
            full_parts.append(f"=== {label} ===\n{df.to_string()}")
            summary_parts.append(
                f"=== {label} ===\n"
                f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
                f"Columns: {', '.join(str(c) for c in df.columns)}\n"
                f"Column types: {', '.join(f'{c}: {t}' for c, t in df.dtypes.items())}\n"
                f"\nFirst 5 rows:\n{df.head(5).to_string()}"
            )

        full_text = "\n\n".join(full_parts)
        summary_text = "\n\n".join(summary_parts)

    except Exception as exc:
        logger.warning(
            "Structured fast-path read failed for %s: %s — using extractor text as fallback",
            raw_file_path, exc,
        )

    chunk = {
        "id": str(uuid.uuid4()),
        "text": summary_text,
        "section_title": "Structured Data Summary",
        "chunk_type": "structured_summary",
        "chunk_index": 0,
        "total_chunks": 1,
        "_raw_file_path": raw_file_path,
    }
    return full_text, [chunk]

async def _process_material(
    material_id: str,
    text: str,
    user_id: str,
    notebook_id: Optional[str],
    *,
    title: Optional[str] = None,
    filename: Optional[str] = None,
    extraction_metadata: Optional[dict] = None,
    source_type: str = "prose",
):
    try:
        if not text or len(text.strip()) < 10:
            await _fail_material(material_id, "Extracted text is too short (< 10 chars)", user_id=user_id)
            return None

        _t_total = time.perf_counter()
        loop = asyncio.get_running_loop()

        _pre_computed_chunks = None
        if source_type in _STRUCTURED_SOURCE_TYPES:
            raw_path = (extraction_metadata or {}).get("upload_path", "")
            from functools import partial as _partial
            full_data, _pre_computed_chunks = await loop.run_in_executor(
                None,
                _partial(_make_structured_summary_chunk, raw_path, text),
            )
            text = full_data
            if extraction_metadata is None:
                extraction_metadata = {}
            extraction_metadata.setdefault("raw_file_path", raw_path)
            extraction_metadata["is_structured"] = True
            logger.info(
                "Structured fast-path: skipping chunker, 1 summary chunk  "
                "material=%s  raw_path=%s",
                material_id, raw_path,
            )

        try:
            _t0 = time.perf_counter()
            await loop.run_in_executor(None, partial(save_material_text, material_id, text))
            logger.info(
                "PERF save_text: %.1fms  material=%s  chars=%d",
                (time.perf_counter() - _t0) * 1000, material_id, len(text),
            )
        except Exception as e:
            logger.error(f"Failed to save text to storage for material {material_id}: {e}")
            await _fail_material(material_id, f"Failed to save text to storage: {e}", user_id=user_id)
            return None

        _t0 = time.perf_counter()
        if _pre_computed_chunks is not None:
            chunks = _pre_computed_chunks
        else:
            chunks = await loop.run_in_executor(
                None,
                partial(chunk_text, text, True, source_type),
            )
        logger.info(
            "PERF chunking: %.1fms  chunks=%d  material=%s",
            (time.perf_counter() - _t0) * 1000, len(chunks), material_id,
        )

        if not chunks and len(text.strip()) > 50:
            logger.error(f"Material {material_id} produced 0 chunks from {len(text)} chars")
            await _fail_material(
                material_id, 
                "Document processing failed: Could not extract searchable content (text might be low quality or unsupported format).", 
                user_id=user_id
            )
            return None

        await _set_status(material_id, "embedding", user_id=user_id)

        summary = get_material_summary(text, max_chars=1000)

        _title_filename = filename
        if not title and not _title_filename:
            try:
                _mat_rec = await prisma.material.find_unique(where={"id": material_id})
                _title_filename = _mat_rec.filename if _mat_rec else None
            except Exception:
                pass

        _t0 = time.perf_counter()

        async def _embed():
            await loop.run_in_executor(
                None,
                partial(
                    embed_and_store,
                    chunks,
                    material_id=material_id,
                    user_id=user_id,
                    notebook_id=notebook_id,
                    filename=filename,
                ),
            )

        await _embed()

        embed_ms = (time.perf_counter() - _t0) * 1000
        logger.info(
            "PERF embedding: %.1fms  chunks=%d  material=%s",
            embed_ms, len(chunks), material_id,
        )

        fast_title: str
        if title:
            fast_title = title
        elif _title_filename:
            fast_title = _title_filename.rsplit(".", 1)[0][:60]
        else:
            fast_title = "Untitled Material"

        update_data: dict = {
            "originalText": sanitize_null_bytes(summary),
            "chunkCount": len(chunks),
            "status": "completed",
            "error": None,
            "title": sanitize_null_bytes(fast_title),
        }

        if extraction_metadata:
            import json
            sanitized_meta = sanitize_null_bytes(extraction_metadata)
            update_data["metadata"] = json.dumps(sanitized_meta)

        result = await prisma.material.update(
            where={"id": material_id},
            data=update_data,
        )
        if filename:
            try:
                from app.services.rag.context_formatter import set_material_name
                set_material_name(material_id, filename)
            except Exception:
                pass
        if user_id:
            await _emit_material_ws(user_id, material_id, "completed", chunk_count=len(chunks))

        logger.info(
            "PERF _process_material total (critical path): %.1fms  material=%s",
            (time.perf_counter() - _t_total) * 1000, material_id,
        )

        if not title:
            _bg_text = text[:2000]
            _bg_filename = _title_filename
            _bg_material_id = material_id
            _bg_user_id = user_id

            async def _background_title_update() -> None:
                try:
                    from app.services.notebook_name_generator import generate_material_title, generate_notebook_name
                    ai_title = await loop.run_in_executor(
                        None,
                        partial(generate_material_title, _bg_text, _bg_filename),
                    )
                    ai_title = sanitize_null_bytes(str(ai_title)[:60])
                    await prisma.material.update(
                        where={"id": _bg_material_id},
                        data={"title": ai_title},
                    )
                    logger.info(
                        "Background AI title updated: material=%s  title='%s'",
                        _bg_material_id, ai_title,
                    )
                    if _bg_user_id:
                        await _emit_material_ws(
                            _bg_user_id, _bg_material_id, "completed",
                            title=ai_title,
                        )
                    
                    if notebook_id and notebook_id != "draft":
                        notebook = await prisma.notebook.find_unique(where={"id": notebook_id})
                        if notebook:
                            import datetime
                            now = datetime.datetime.now(datetime.timezone.utc)
                            time_diff = now - notebook.createdAt.replace(tzinfo=datetime.timezone.utc)
                            
                            import os
                            stem = os.path.splitext(_bg_filename or "")[0][:40].strip()
                            
                            is_default_name = (
                                notebook.name.startswith("New Notebook") or 
                                notebook.name.startswith("Untitled") or 
                                notebook.name.startswith("Notebook 20") or 
                                (stem and notebook.name == stem)
                            )
                            
                            if time_diff.total_seconds() < 300 and is_default_name:
                                ai_notebook_name = await loop.run_in_executor(
                                    None,
                                    partial(generate_notebook_name, _bg_text, _bg_filename),
                                )
                                ai_notebook_name = sanitize_null_bytes(str(ai_notebook_name)[:200])
                                await prisma.notebook.update(
                                    where={"id": notebook_id},
                                    data={"name": ai_notebook_name},
                                )
                                logger.info(
                                    "Background AI notebook name updated: notebook=%s  name='%s'",
                                    notebook_id, ai_notebook_name,
                                )
                                
                                if _bg_user_id:
                                    try:
                                        from app.services.ws_manager import ws_manager
                                        await ws_manager.send_to_user(
                                            _bg_user_id, 
                                            {"type": "notebook_update", "notebook_id": notebook_id, "name": ai_notebook_name}
                                        )
                                    except Exception as ws_exc:
                                        logger.debug("Notebook update WS emit failed: %s", ws_exc)

                except Exception as bg_exc:
                    logger.warning(
                        "Background title/notebook generation failed for material %s: %s",
                        _bg_material_id, bg_exc,
                    )

            asyncio.create_task(_background_title_update())

        return result

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=user_id)
        return None

async def create_material_record(
    filename: str,
    user_id,
    notebook_id=None,
    source_type: str = "file",
    title: Optional[str] = None,
) -> str:
    uid = str(user_id)
    nid = str(notebook_id) if notebook_id and notebook_id != "draft" else None
    data: dict = {
        "filename": filename,
        "userId": uid,
        "status": "pending",
        "sourceType": source_type,
    }
    if nid:
        data["notebookId"] = nid
    if title:
        data["title"] = title
    material = await prisma.material.create(data=data)
    logger.info("Created material record %s (pending) for user %s", material.id, uid)
    return str(material.id)

async def process_material_by_id(
    material_id: str,
    file_path: str,
    filename: str,
    user_id: str,
    notebook_id: Optional[str] = None,
) -> None:
    uid = str(user_id)
    nid = str(notebook_id) if notebook_id and notebook_id != "draft" else None
    loop = asyncio.get_running_loop()
    _t_total = time.perf_counter()

    try:
        await _set_status(material_id, "processing", user_id=uid)

        from app.services.text_processing.extractor import EnhancedTextExtractor
        from app.services.text_processing.file_detector import FileTypeDetector

        file_info = FileTypeDetector.detect_file_type(file_path)
        category = file_info.get("category", "document")
        if category == "image":
            await _set_status(material_id, "ocr_running", user_id=uid)
        elif category in ("audio", "video"):
            await _set_status(material_id, "transcribing", user_id=uid)

        extractor = EnhancedTextExtractor()
        _t_extract = time.perf_counter()
        result = await loop.run_in_executor(
            None,
            partial(extractor.extract_text, file_path, source_type="file"),
        )
        logger.info(
            "PERF extraction: %.1fms  material=%s  category=%s",
            (time.perf_counter() - _t_extract) * 1000, material_id, category,
        )

        if result["status"] != "success":
            error_msg = result.get("error", "unknown extraction error")
            await _fail_material(material_id, f"Extraction failed: {error_msg}", user_id=uid)
            return

        extraction_metadata = result.get("metadata", {})
        extraction_metadata["upload_path"] = file_path
        await _process_material(
            material_id,
            result["text"],
            uid,
            nid,
            filename=filename,
            extraction_metadata=extraction_metadata,
            source_type=result.get("source_type") or extraction_metadata.get("source_type", "prose"),
        )
        logger.info(
            "PERF process_material_by_id total: %.1fms  material=%s",
            (time.perf_counter() - _t_total) * 1000, material_id,
        )

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=uid)

async def filter_completed_material_ids(
    material_ids: List[str],
    user_id: str,
) -> List[str]:
    if not material_ids:
        return []
    materials = await prisma.material.find_many(
        where={"id": {"in": material_ids}, "userId": str(user_id), "status": "completed"},
    )
    completed_set = {str(m.id) for m in materials}
    return [mid for mid in material_ids if mid in completed_set]

async def process_url_material_by_id(
    material_id: str,
    url: str,
    user_id: str,
    notebook_id: Optional[str] = None,
    source_type: str = "auto",
):
    uid, nid = str(user_id), str(notebook_id) if notebook_id and notebook_id != "draft" else None
    
    try:
        await _set_status(material_id, "processing", user_id=uid)

        from app.services.text_processing.extractor import EnhancedTextExtractor

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(EnhancedTextExtractor().extract_text, url, source_type=source_type),
        )

        if result["status"] != "success":
            error_msg = result.get("error", "unknown extraction error")
            await _fail_material(material_id, f"URL extraction failed: {error_msg}", user_id=uid)
            return

        title = result.get("title", url)
        extraction_metadata = result.get("metadata", {})
        from urllib.parse import urlparse as _urlparse
        _parsed = _urlparse(url)
        url_filename = title or _parsed.netloc or url

        await _process_material(
            material_id,
            result["text"],
            uid,
            nid,
            title=title,
            filename=url_filename,
            extraction_metadata=extraction_metadata,
            source_type=extraction_metadata.get("source_type", "prose"),
        )

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=uid)

async def process_text_material_by_id(
    material_id: str,
    text_content: str,
    title: str,
    user_id: str,
    notebook_id: Optional[str] = None,
):
    uid, nid = str(user_id), str(notebook_id) if notebook_id and notebook_id != "draft" else None

    try:
        await _set_status(material_id, "processing", user_id=uid)
        await _process_material(material_id, text_content, uid, nid, title=title, filename=title)
    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=uid)

async def get_material(material_id: str):
    return await prisma.material.find_unique(where={"id": material_id})

async def get_material_for_user(material_id: str, user_id):
    return await prisma.material.find_first(
        where={"id": str(material_id), "userId": str(user_id)}
    )

async def get_material_text(material_id: str, user_id: str) -> Optional[str]:
    material = await get_material_for_user(material_id, user_id)
    if not material:
        logger.warning(f"Material {material_id} not found or unauthorized for user {user_id}")
        return None
    
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, load_material_text, material_id)
        return text
    except FileNotFoundError:
        logger.error(f"Full text file not found for material {material_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to load text for material {material_id}: {e}")
        return None

async def get_user_materials(user_id, notebook_id=None) -> list:
    where: dict = {"userId": str(user_id)}
    if notebook_id and notebook_id != "draft":
        where["notebookId"] = str(notebook_id)
    elif notebook_id == "draft":
        where["notebookId"] = None
    return await prisma.material.find_many(where=where, order={"createdAt": "desc"})

async def update_material(
    material_id: str,
    user_id,
    filename: Optional[str] = None,
    title: Optional[str] = None,
):
    material = await get_material_for_user(material_id, user_id)
    if not material:
        return None
    data: dict = {}
    if filename is not None:
        data["filename"] = filename
    if title is not None:
        data["title"] = title
    if not data:
        return material
    return await prisma.material.update(where={"id": material.id}, data=data)

async def delete_material(material_id: str, user_id) -> bool:
    material = await get_material_for_user(material_id, user_id)
    if not material:
        return False

    loop = asyncio.get_running_loop()
    step_completed = {"chroma": False, "files": False, "db": False}

    try:
        try:
            from app.db.chroma import get_collection
            collection = get_collection()
            await loop.run_in_executor(
                None, lambda: collection.delete(where={"material_id": str(material_id)})
            )
            step_completed["chroma"] = True
            logger.info("Deleted ChromaDB embeddings for material %s", material_id)
        except Exception as e:
            logger.error("Step 1 FAILED (ChromaDB delete) for material %s: %s", material_id, e)
            raise RuntimeError(f"ChromaDB delete failed: {e}") from e

        try:
            await loop.run_in_executor(None, delete_material_text, material_id)
            if material.filename:
                import glob
                upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
                for pattern in (
                    os.path.join(upload_dir, f"*_{material.filename}"),
                    os.path.join(upload_dir, f"{material_id}_*"),
                ):
                    for fpath in glob.glob(pattern):
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                            logger.info("Deleted upload file: %s", fpath)
            step_completed["files"] = True
            logger.info("Deleted file storage for material %s", material_id)
        except Exception as e:
            logger.error("Step 2 FAILED (file delete) for material %s: %s", material_id, e)
            raise RuntimeError(f"File delete failed: {e}") from e

        try:
            await prisma.material.delete(where={"id": material.id})
            step_completed["db"] = True
            logger.info("Deleted material record %s", material_id)
        except Exception as e:
            logger.error("Step 3 FAILED (DB delete) for material %s: %s", material_id, e)
            raise RuntimeError(f"DB delete failed: {e}") from e

        return True

    except RuntimeError as exc:
        logger.error(
            "Material delete partial failure for %s — completed steps: %s — error: %s",
            material_id, step_completed, exc,
        )
        if step_completed["chroma"] and not step_completed["db"]:
            try:
                await prisma.material.update(
                    where={"id": material.id},
                    data={"status": "failed", "error": f"Partial delete: {exc}"},
                )
            except Exception:
                pass
        return False
