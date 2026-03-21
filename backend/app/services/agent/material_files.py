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


def _read_file_schema(fname: str, fpath: str, ext: str) -> str:
    """Read columns, dtypes, and sample rows directly from a structured file."""
    try:
        import pandas as pd
        if ext == ".csv":
            df = pd.read_csv(fpath, nrows=5, encoding_errors="replace")
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(fpath, nrows=5)
        elif ext == ".tsv":
            df = pd.read_csv(fpath, sep="\t", nrows=5, encoding_errors="replace")
        elif ext == ".parquet":
            import pyarrow.parquet as pq  # noqa: F401
            df = pd.read_parquet(fpath).head(5)
        elif ext == ".ods":
            df = pd.read_excel(fpath, engine="odf", nrows=5)
        else:
            return ""
        parts = [f"    Schema ({len(df.columns)} columns):"]
        parts.append(f"    Columns: {', '.join(str(c) for c in df.columns)}")
        dtypes_str = ", ".join(f"{c}({t})" for c, t in df.dtypes.items())
        parts.append(f"    Types:   {dtypes_str}")
        sample = df.head(3).to_string(index=False)
        indented = "\n".join("    " + line for line in sample.splitlines())
        parts.append(f"    Sample (first 3 rows):\n{indented}")
        return "\n".join(parts)
    except Exception as exc:
        logger.debug("Could not read schema for '%s': %s", fname, exc)
        return ""


def build_files_prompt_section(file_map: Dict[str, str]) -> str:
    """Build the prompt section listing available dataset files with inline schema."""
    if not file_map:
        return ""
    lines = ["AVAILABLE DATASET FILES (already in working directory — use these exact names):"]
    for fname, fpath in file_map.items():
        ext = os.path.splitext(fname)[1].lower()
        if ext == ".csv":
            hint = f"  → pd.read_csv('{fname}')"
        elif ext in (".xlsx", ".xls"):
            hint = f"  → pd.read_excel('{fname}')"
        elif ext == ".parquet":
            hint = f"  → pd.read_parquet('{fname}')"
        elif ext == ".json":
            hint = f"  → pd.read_json('{fname}')"
        else:
            hint = ""
        lines.append(f"  - {fname}{hint}")
        if ext in (".csv", ".xlsx", ".xls", ".tsv", ".ods", ".parquet"):
            schema = _read_file_schema(fname, fpath, ext)
            if schema:
                lines.append(schema)
    lines.append(
        "\nCRITICAL: Use ONLY the filenames listed above. "
        "Do NOT invent filenames like 'dataset.csv' or 'data.csv'. "
        "Reference the exact column names shown in the schema above."
    )
    return "\n".join(lines)
