from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
def healthcheck() -> dict[str, Any]:
    # `demo` est public : la page de connexion affiche alors les identifiants de démonstration
    return {"status": "ok", "demo": settings.DEMO_MODE}
