"""Models API — status and reload of required AI models."""

from fastapi import APIRouter, Depends, HTTPException
from app.services.model_manager import model_manager
from app.services.auth import get_current_user
from app.models.model_schemas import (
    ModelStatus,
    ModelsSummary,
    ModelsStatusResponse,
    ModelsReloadResponse,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status", response_model=ModelsStatusResponse)
async def get_models_status(current_user=Depends(get_current_user)):
    """Get status of all required models (requires authentication)."""
    info = model_manager.get_model_info()
    status_map: dict[str, ModelStatus] = {}

    for model_id, cfg in info["required_models"].items():
        name = cfg["name"]
        available = model_manager._is_model_cached(name)
        status_map[model_id] = ModelStatus(
            name=name,
            type=cfg["type"],
            required=cfg["required"],
            description=cfg.get("description", ""),
            available=available,
            status="ready" if available else "missing",
        )

    ready = sum(1 for m in status_map.values() if m.available)
    return ModelsStatusResponse(
        models_directory=info["models_directory"],
        cache_size=info["cache_size"],
        models=status_map,
        summary=ModelsSummary(
            total=len(status_map),
            ready=ready,
            missing=len(status_map) - ready,
        ),
    )


@router.post("/reload", response_model=ModelsReloadResponse)
async def reload_models(current_user=Depends(get_current_user)):
    """Reload and revalidate all models. Requires admin role."""
    if getattr(current_user, "role", None) != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    results = await model_manager.validate_and_load_models()
    return ModelsReloadResponse(
        message="Model reload completed",
        results=results,
        success=all(results.values()),
    )