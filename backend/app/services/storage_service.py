from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

MATERIAL_TEXT_DIR = Path(settings.UPLOAD_DIR).parent / "material_text"

_UUID_RE = re.compile(r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$", re.I)

def _validate_material_id(material_id: str) -> None:
    if not material_id or not _UUID_RE.match(material_id):
        raise ValueError(f"Invalid material_id format: {material_id!r}")

def _ensure_storage_dir() -> None:
    MATERIAL_TEXT_DIR.mkdir(parents=True, exist_ok=True)

def save_material_text(material_id: str, text: str) -> bool:
    try:
        _validate_material_id(material_id)
        _ensure_storage_dir()
        
        file_path = MATERIAL_TEXT_DIR / f"{material_id}.txt"
        
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        
        logger.info(f"Saved material text: {material_id} ({len(text)} chars)")
        return True
        
    except ValueError as e:
        logger.error(f"Invalid material_id: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save material text {material_id}: {e}")
        return False

def load_material_text(material_id: str) -> Optional[str]:
    try:
        _validate_material_id(material_id)
        file_path = MATERIAL_TEXT_DIR / f"{material_id}.txt"
        
        if not file_path.exists():
            logger.warning(f"Material text not found: {material_id}")
            return None
        
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        
        logger.debug(f"Loaded material text: {material_id} ({len(text)} chars)")
        return text
        
    except ValueError as e:
        logger.error(f"Invalid material_id: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load material text {material_id}: {e}")
        return None

def delete_material_text(material_id: str) -> bool:
    try:
        _validate_material_id(material_id)
        file_path = MATERIAL_TEXT_DIR / f"{material_id}.txt"
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted material text: {material_id}")
            return True
        else:
            logger.warning(f"Material text not found for deletion: {material_id}")
            return False
        
    except ValueError as e:
        logger.error(f"Invalid material_id: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete material text {material_id}: {e}")
        return False

def get_material_summary(text: str, max_chars: int = 1000) -> str:
    if not text:
        return ""
    
    summary = text[:max_chars]
    
    if len(text) > max_chars:
        last_period = summary.rfind(". ")
        if last_period > max_chars // 2:
            summary = summary[:last_period + 1]
        summary += "..."
    
    return summary

def delete_uploaded_file(file_path: str) -> bool:
    try:
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink()
            logger.info("Deleted uploaded file: %s", file_path)
            return True
        return False
    except Exception as e:
        logger.error("Failed to delete uploaded file %s: %s", file_path, e)
        return False
