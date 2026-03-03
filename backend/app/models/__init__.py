"""Pydantic schemas for structured data.

Database models are defined in ``prisma/schema.prisma``.
All DB operations use the Prisma client (``app.db.prisma_client``).

Non-LLM AI model registry and response schemas are in ``model_schemas``.
"""

from app.models.model_schemas import (  # noqa: F401
    ModelConfig,
    ModelStatus,
    ModelsSummary,
    ModelsStatusResponse,
    ModelsReloadResponse,
    REQUIRED_MODELS,
    get_local_model_path,
    is_model_local,
)
