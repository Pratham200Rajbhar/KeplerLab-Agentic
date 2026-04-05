from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["metrics"])

try:
    from prometheus_client import make_asgi_app
    if settings.ENABLE_PROMETHEUS:
        metrics_app = make_asgi_app()
        
        @router.get("/metrics")
        async def metrics(request):
            # This is a bit of a hack because make_asgi_app returns an ASGIV2 app
            # but we can mount it or use it directly. 
            # For simplicity in router, we can just use the app.
            return await metrics_app(request.scope, request.receive, request.send)
    else:
        @router.get("/metrics")
        async def metrics():
            return {"detail": "Prometheus metrics are disabled."}
except ImportError:
    @router.get("/metrics")
    async def metrics():
        return {"detail": "prometheus_client not installed."}
