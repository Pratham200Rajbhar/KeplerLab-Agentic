"""
Utility to resolve uploaded material files from disk so that generated code
and the sandbox can reference / copy them by their real names.
"""
from __future__ import annotations

import glob
import logging
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_material_file_map(
    material_ids: List[str],
    user_id: str,
) -> Dict[str, str]:
    """
    Return {original_filename: absolute_disk_path} for every material that
    has an uploadable file on disk.

    Lookup strategy:
    1. Query Prisma for material records to get the real filename.
    2. Glob under {UPLOAD_DIR}/{user_id}/ for a file matching *_{filename}.
       - Handles filenames with spaces / parentheses fine.
       - Escapes glob metacharacters ([, ], *, ?) that may appear in filenames.
    """
    if not material_ids:
        return {}

    from app.db.prisma_client import prisma

    try:
        materials = await prisma.material.find_many(
            where={"id": {"in": material_ids}},
            take=len(material_ids),
        )
    except Exception as exc:
        logger.warning("Could not fetch material records: %s", exc)
        return {}

    upload_root = os.path.abspath(settings.UPLOAD_DIR)
    user_dir = os.path.join(upload_root, str(user_id))

    result: Dict[str, str] = {}

    for mat in materials:
        if not mat.filename:
            continue
        original_name = mat.filename

        # Escape glob metacharacters in the filename portion
        escaped = re.sub(r"([\[\]*?])", r"[\1]", original_name)
        pattern = os.path.join(user_dir, f"*_{escaped}")
        matches = glob.glob(pattern)

        if matches:
            # Prefer the most recently modified file if multiple match
            matches.sort(key=os.path.getmtime, reverse=True)
            result[original_name] = matches[0]
            logger.debug("Resolved material '%s' → %s", original_name, matches[0])
        else:
            logger.warning(
                "Could not find upload file for material '%s' (id=%s)",
                original_name, mat.id,
            )

    return result


def copy_materials_to_workdir(
    file_map: Dict[str, str],
    work_dir: str,
) -> List[str]:
    """
    Copy material files into the sandbox work directory using their original names.
    Returns list of filenames successfully copied.
    """
    copied: List[str] = []
    for filename, src_path in file_map.items():
        dest = os.path.join(work_dir, filename)
        # Skip if already present (idempotent)
        if os.path.exists(dest):
            copied.append(filename)
            continue
        try:
            shutil.copy2(src_path, dest)
            copied.append(filename)
            logger.debug("Copied '%s' to work_dir", filename)
        except Exception as exc:
            logger.warning("Failed to copy material '%s': %s", filename, exc)
    return copied


def build_files_prompt_section(file_map: Dict[str, str]) -> str:
    """Build the prompt section listing available dataset files."""
    if not file_map:
        return ""
    lines = ["AVAILABLE DATASET FILES (already in working directory — use these exact names):"]
    for fname in file_map:
        ext = os.path.splitext(fname)[1].lower()
        hint = ""
        if ext in (".csv",):
            hint = "  → load with: pd.read_csv('{name}')".format(name=fname)
        elif ext in (".xlsx", ".xls"):
            hint = "  → load with: pd.read_excel('{name}')".format(name=fname)
        elif ext in (".parquet",):
            hint = "  → load with: pd.read_parquet('{name}')".format(name=fname)
        elif ext in (".json",):
            hint = "  → load with: pd.read_json('{name}')".format(name=fname)
        lines.append(f"  - {fname}{hint}")
    lines.append(
        "\nCRITICAL: Use ONLY the filenames listed above. "
        "Do NOT invent filenames like 'dataset.csv' or 'data.csv'."
    )
    return "\n".join(lines)
