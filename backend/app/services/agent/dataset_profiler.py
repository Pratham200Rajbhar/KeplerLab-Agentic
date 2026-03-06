"""Dataset Profiler — Computes rich dataset profiles before agent planning.

Automatically profiles uploaded datasets to give the LLM detailed
understanding of data distribution, correlations, missing values,
and semantic patterns — instead of just column names + head().

Usage in the pipeline:
    profiler = DatasetProfiler(material_ids, user_id, work_dir)
    profiles = await profiler.profile_all()
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)

# Maximum rows to load for profiling large datasets
_MAX_PROFILE_ROWS = 50_000
# Sample size for random sample display
_SAMPLE_ROWS = 10
# Max columns to include in correlation matrix output
_MAX_CORR_COLUMNS = 30
# Threshold below which a numeric column is treated as categorical
_UNIQUE_RATIO_CATEGORICAL = 0.02  # < 2% unique values relative to row count


@dataclass
class ColumnProfile:
    """Profile for a single column."""
    name: str
    dtype: str
    is_numeric: bool = False
    is_categorical: bool = False
    missing_count: int = 0
    missing_pct: float = 0.0
    unique_count: int = 0
    # Numeric stats
    mean: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    q25: Optional[float] = None
    median: Optional[float] = None
    q75: Optional[float] = None
    max_val: Optional[float] = None
    # Categorical stats
    top_values: Optional[List[Tuple[str, int]]] = None  # (value, count) pairs

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "dtype": self.dtype,
            "is_numeric": self.is_numeric,
            "is_categorical": self.is_categorical,
            "missing_count": self.missing_count,
            "missing_pct": round(self.missing_pct, 2),
            "unique_count": self.unique_count,
        }
        if self.is_numeric:
            d.update({
                "mean": _safe_round(self.mean),
                "std": _safe_round(self.std),
                "min": _safe_round(self.min_val),
                "q25": _safe_round(self.q25),
                "median": _safe_round(self.median),
                "q75": _safe_round(self.q75),
                "max": _safe_round(self.max_val),
            })
        if self.top_values:
            d["top_values"] = [
                {"value": str(v), "count": c} for v, c in self.top_values
            ]
        return d


@dataclass
class DatasetProfile:
    """Complete profile of a single dataset."""
    name: str
    file_path: str
    rows: int = 0
    columns: int = 0
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    datetime_columns: List[str] = field(default_factory=list)
    column_profiles: List[ColumnProfile] = field(default_factory=list)
    correlations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    top_correlations: List[Tuple[str, str, float]] = field(default_factory=list)
    sample_rows: List[Dict[str, Any]] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    is_sampled: bool = False
    sample_size: int = 0
    profiling_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "rows": self.rows,
            "columns": self.columns,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "datetime_columns": self.datetime_columns,
            "column_profiles": [cp.to_dict() for cp in self.column_profiles],
            "correlations": self.correlations,
            "top_correlations": [
                {"col1": c1, "col2": c2, "value": round(v, 4)}
                for c1, c2, v in self.top_correlations
            ],
            "sample_rows": self.sample_rows,
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "is_sampled": self.is_sampled,
            "sample_size": self.sample_size,
        }

    def to_context_string(self) -> str:
        """Format the profile as a concise text block for LLM context injection."""
        parts: List[str] = []

        parts.append(f"=== Dataset Profile: {self.name} ===")
        parts.append(f"Shape: {self.rows:,} rows × {self.columns} columns")
        if self.is_sampled:
            parts.append(f"(Profiled on a sample of {self.sample_size:,} rows)")
        parts.append(f"Memory: ~{self.memory_usage_mb:.1f} MB")

        # Column types
        if self.numeric_columns:
            parts.append(f"Numeric columns ({len(self.numeric_columns)}): {', '.join(self.numeric_columns)}")
        if self.categorical_columns:
            parts.append(f"Categorical columns ({len(self.categorical_columns)}): {', '.join(self.categorical_columns)}")
        if self.datetime_columns:
            parts.append(f"Datetime columns ({len(self.datetime_columns)}): {', '.join(self.datetime_columns)}")

        # Missing values
        missing_cols = [
            cp for cp in self.column_profiles if cp.missing_count > 0
        ]
        if missing_cols:
            parts.append("\nMissing Values:")
            for cp in sorted(missing_cols, key=lambda c: -c.missing_pct):
                parts.append(f"  {cp.name}: {cp.missing_count:,} ({cp.missing_pct:.1f}%)")
        else:
            parts.append("\nMissing Values: None")

        # Numeric statistics
        numeric_profiles = [cp for cp in self.column_profiles if cp.is_numeric]
        if numeric_profiles:
            parts.append("\nNumeric Statistics:")
            for cp in numeric_profiles:
                parts.append(
                    f"  {cp.name}: mean={_fmt(cp.mean)}, std={_fmt(cp.std)}, "
                    f"min={_fmt(cp.min_val)}, median={_fmt(cp.median)}, max={_fmt(cp.max_val)}"
                )

        # Categorical value counts
        cat_profiles = [cp for cp in self.column_profiles if cp.is_categorical and cp.top_values]
        if cat_profiles:
            parts.append("\nCategorical Value Counts (top 5):")
            for cp in cat_profiles:
                vals = ", ".join(f"{v}({c})" for v, c in (cp.top_values or [])[:5])
                parts.append(f"  {cp.name} [{cp.unique_count} unique]: {vals}")

        # Top correlations
        if self.top_correlations:
            parts.append("\nTop Correlations:")
            for c1, c2, val in self.top_correlations[:10]:
                parts.append(f"  {c1} ↔ {c2}: {val:.4f}")

        # Sample rows
        if self.sample_rows:
            parts.append(f"\nRandom Sample ({len(self.sample_rows)} rows):")
            # Format as a mini-table (column names + values)
            cols = list(self.sample_rows[0].keys())
            header = " | ".join(str(c)[:20] for c in cols)
            parts.append(f"  {header}")
            parts.append(f"  {'─' * min(len(header), 120)}")
            for row in self.sample_rows[:_SAMPLE_ROWS]:
                vals = " | ".join(str(row.get(c, ""))[:20] for c in cols)
                parts.append(f"  {vals}")

        return "\n".join(parts)


class DatasetProfiler:
    """Profiles datasets from uploaded materials before agent planning.

    Workflow:
      1. Resolve file paths for structured materials (CSV/Excel/TSV)
      2. Copy files into the sandbox work_dir
      3. Compute profiling stats using pandas
      4. Return structured DatasetProfile objects
    """

    # Extensions recognized as structured/tabular
    STRUCTURED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".tsv", ".ods"}

    def __init__(
        self,
        material_ids: List[str],
        user_id: str,
        work_dir: str,
    ):
        self.material_ids = material_ids
        self.user_id = user_id
        self.work_dir = work_dir

    async def profile_all(self) -> List[DatasetProfile]:
        """Profile all structured datasets from the given material IDs.

        Returns a list of DatasetProfile objects (one per file).
        Non-structured materials (PDFs, docs, etc.) are skipped.
        """
        if not self.material_ids:
            return []

        # Step 1: Resolve file paths from the database
        file_infos = await self._resolve_material_files()
        if not file_infos:
            return []

        # Step 2: Profile each file
        profiles: List[DatasetProfile] = []
        loop = asyncio.get_running_loop()

        for filename, file_path in file_infos:
            try:
                profile = await loop.run_in_executor(
                    None,
                    self._profile_single_file,
                    filename,
                    file_path,
                )
                if profile:
                    profiles.append(profile)
            except Exception as exc:
                logger.warning("Failed to profile %s: %s", filename, exc)
                profiles.append(DatasetProfile(
                    name=filename,
                    file_path=file_path,
                    profiling_error=str(exc),
                ))

        return profiles

    async def _resolve_material_files(self) -> List[Tuple[str, str]]:
        """Query DB for material metadata and resolve raw file paths.

        Returns list of (filename, absolute_file_path) for structured files.
        """
        if not self.material_ids:
            return []

        try:
            materials = await prisma.material.find_many(
                where={
                    "id": {"in": self.material_ids},
                    "userId": self.user_id,
                    "status": "completed",
                },
            )
        except Exception as exc:
            logger.error("Failed to query materials: %s", exc)
            return []

        results: List[Tuple[str, str]] = []

        for mat in materials:
            filename = mat.filename or ""
            ext = Path(filename).suffix.lower()

            if ext not in self.STRUCTURED_EXTENSIONS:
                continue

            # Resolve file path from metadata
            file_path = self._resolve_file_path(mat)
            if not file_path or not os.path.isfile(file_path):
                logger.warning(
                    "Cannot locate file for material %s (%s): path=%s",
                    mat.id, filename, file_path,
                )
                continue

            # Copy into work_dir so the sandbox can access it
            dest_path = os.path.join(self.work_dir, filename)
            if not os.path.exists(dest_path):
                try:
                    shutil.copy2(file_path, dest_path)
                except Exception as exc:
                    logger.warning("Failed to copy %s to work_dir: %s", filename, exc)
                    # Still try to profile from original path
                    dest_path = file_path

            results.append((filename, dest_path))

        return results

    @staticmethod
    def _resolve_file_path(material) -> Optional[str]:
        """Extract the raw file path from material metadata.

        Checks multiple locations where the upload path might be stored.
        """
        metadata = material.metadata if material.metadata else {}
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        # Try extraction metadata paths
        for key in ("upload_path", "raw_file_path", "file_path", "path"):
            val = metadata.get(key, "")
            if val and os.path.isfile(val):
                return val

        # Fallback: reconstruct from UPLOAD_DIR
        user_id = str(material.userId)
        filename = material.filename or ""
        if filename:
            candidate = os.path.join(settings.UPLOAD_DIR, user_id, filename)
            if os.path.isfile(candidate):
                return candidate

        return None

    def _profile_single_file(
        self,
        filename: str,
        file_path: str,
    ) -> Optional[DatasetProfile]:
        """Profile a single dataset file using pandas.

        Uses sampling for large datasets to keep profiling fast.
        """
        import pandas as pd
        import numpy as np

        ext = Path(file_path).suffix.lower()

        # Read dataset (with sampling for large files)
        try:
            if ext == ".csv":
                df_full = pd.read_csv(file_path, encoding_errors="replace", nrows=5)
                total_rows = _count_csv_rows(file_path)
                if total_rows > _MAX_PROFILE_ROWS:
                    # Sample for profiling
                    df = pd.read_csv(
                        file_path,
                        encoding_errors="replace",
                        skiprows=lambda i: i > 0 and i % max(1, total_rows // _MAX_PROFILE_ROWS) != 0,
                        nrows=_MAX_PROFILE_ROWS,
                    )
                    is_sampled = True
                    sample_size = len(df)
                else:
                    df = pd.read_csv(file_path, encoding_errors="replace")
                    is_sampled = False
                    sample_size = len(df)
                    total_rows = len(df)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(file_path)
                total_rows = len(df)
                is_sampled = False
                sample_size = total_rows
                if total_rows > _MAX_PROFILE_ROWS:
                    df = df.sample(n=_MAX_PROFILE_ROWS, random_state=42)
                    is_sampled = True
                    sample_size = _MAX_PROFILE_ROWS
            elif ext == ".tsv":
                df = pd.read_csv(file_path, sep="\t", encoding_errors="replace")
                total_rows = len(df)
                is_sampled = False
                sample_size = total_rows
                if total_rows > _MAX_PROFILE_ROWS:
                    df = df.sample(n=_MAX_PROFILE_ROWS, random_state=42)
                    is_sampled = True
                    sample_size = _MAX_PROFILE_ROWS
            elif ext == ".ods":
                df = pd.read_excel(file_path, engine="odf")
                total_rows = len(df)
                is_sampled = False
                sample_size = total_rows
            else:
                return None
        except Exception as exc:
            logger.warning("Failed to read %s: %s", file_path, exc)
            return DatasetProfile(
                name=filename,
                file_path=file_path,
                profiling_error=f"Read error: {exc}",
            )

        # ── Classify columns ─────────────────────────────────
        numeric_cols: List[str] = []
        categorical_cols: List[str] = []
        datetime_cols: List[str] = []

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                # Check if it's actually categorical (few unique values)
                nunique = df[col].nunique()
                if total_rows > 0 and nunique / max(total_rows, 1) < _UNIQUE_RATIO_CATEGORICAL and nunique <= 20:
                    categorical_cols.append(str(col))
                else:
                    numeric_cols.append(str(col))
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_cols.append(str(col))
            else:
                # Try to parse as datetime
                try:
                    pd.to_datetime(df[col], errors="raise", format="mixed")
                    datetime_cols.append(str(col))
                except (ValueError, TypeError):
                    categorical_cols.append(str(col))

        # ── Column profiles ───────────────────────────────────
        column_profiles: List[ColumnProfile] = []

        for col in df.columns:
            col_str = str(col)
            missing = int(df[col].isna().sum())
            missing_pct = (missing / total_rows * 100) if total_rows > 0 else 0.0
            nunique = int(df[col].nunique())

            cp = ColumnProfile(
                name=col_str,
                dtype=str(df[col].dtype),
                is_numeric=col_str in numeric_cols,
                is_categorical=col_str in categorical_cols,
                missing_count=missing,
                missing_pct=missing_pct,
                unique_count=nunique,
            )

            if col_str in numeric_cols:
                desc = df[col].describe()
                cp.mean = _to_float(desc.get("mean"))
                cp.std = _to_float(desc.get("std"))
                cp.min_val = _to_float(desc.get("min"))
                cp.q25 = _to_float(desc.get("25%"))
                cp.median = _to_float(desc.get("50%"))
                cp.q75 = _to_float(desc.get("75%"))
                cp.max_val = _to_float(desc.get("max"))

            if col_str in categorical_cols:
                vc = df[col].value_counts().head(10)
                cp.top_values = [(str(idx), int(cnt)) for idx, cnt in vc.items()]

            column_profiles.append(cp)

        # ── Correlation matrix ────────────────────────────────
        correlations: Dict[str, Dict[str, float]] = {}
        top_correlations: List[Tuple[str, str, float]] = []

        num_df = df[numeric_cols[:_MAX_CORR_COLUMNS]].select_dtypes(include=[np.number])
        if len(num_df.columns) >= 2:
            try:
                corr_matrix = num_df.corr()
                # Store as nested dict
                correlations = {
                    str(c1): {
                        str(c2): round(float(corr_matrix.loc[c1, c2]), 4)
                        for c2 in corr_matrix.columns
                    }
                    for c1 in corr_matrix.index
                }
                # Extract top absolute correlations (excluding self-correlations)
                pairs_seen = set()
                sorted_pairs = []
                for c1 in corr_matrix.columns:
                    for c2 in corr_matrix.columns:
                        if c1 >= c2:
                            continue
                        pair_key = (str(c1), str(c2))
                        if pair_key not in pairs_seen:
                            pairs_seen.add(pair_key)
                            val = float(corr_matrix.loc[c1, c2])
                            if not np.isnan(val):
                                sorted_pairs.append((str(c1), str(c2), val))

                sorted_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
                top_correlations = sorted_pairs[:15]
            except Exception as exc:
                logger.debug("Correlation computation failed: %s", exc)

        # ── Random sample ─────────────────────────────────────
        sample_n = min(_SAMPLE_ROWS, len(df))
        if sample_n > 0:
            sample_df = df.sample(n=sample_n, random_state=42)
            sample_rows = []
            for _, row in sample_df.iterrows():
                sample_rows.append({
                    str(col): _serialize_value(row[col])
                    for col in df.columns
                })
        else:
            sample_rows = []

        # ── Memory usage ──────────────────────────────────────
        memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

        return DatasetProfile(
            name=filename,
            file_path=file_path,
            rows=total_rows,
            columns=len(df.columns),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            datetime_columns=datetime_cols,
            column_profiles=column_profiles,
            correlations=correlations,
            top_correlations=top_correlations,
            sample_rows=sample_rows,
            memory_usage_mb=memory_mb,
            is_sampled=is_sampled,
            sample_size=sample_size,
        )


# ── Helpers ───────────────────────────────────────────────────


def _count_csv_rows(path: str) -> int:
    """Fast line count for a CSV (approximate row count)."""
    count = 0
    try:
        with open(path, "rb") as f:
            for _ in f:
                count += 1
        return max(count - 1, 0)  # Subtract header
    except Exception:
        return 0


def _to_float(val: Any) -> Optional[float]:
    """Safely convert a value to float."""
    if val is None:
        return None
    try:
        import numpy as np
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _safe_round(val: Optional[float], decimals: int = 4) -> Optional[float]:
    """Round a float safely."""
    if val is None:
        return None
    return round(val, decimals)


def _fmt(val: Optional[float]) -> str:
    """Format a float for display."""
    if val is None:
        return "N/A"
    if abs(val) >= 1000:
        return f"{val:,.2f}"
    return f"{val:.4f}"


def _serialize_value(val: Any) -> Any:
    """Serialize a pandas value for JSON output."""
    import numpy as np
    import pandas as pd

    if pd.isna(val):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        f = float(val)
        return None if np.isnan(f) else f
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return str(val) if not isinstance(val, (int, float, bool, str)) else val


def build_combined_profile_context(profiles: List[DatasetProfile]) -> str:
    """Combine multiple dataset profiles into a single context string.

    Used to inject into both the planning prompt and code generation prompt.
    """
    if not profiles:
        return ""

    parts = ["═══ DATASET PROFILING RESULTS ═══\n"]
    for i, profile in enumerate(profiles):
        if profile.profiling_error:
            parts.append(
                f"Dataset {i + 1}: {profile.name} — profiling failed: {profile.profiling_error}\n"
            )
        else:
            parts.append(profile.to_context_string())
            parts.append("")  # blank line separator

    parts.append("═══ END DATASET PROFILES ═══")
    return "\n".join(parts)
