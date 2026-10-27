from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck():
    # `demo` est public : la page de connexion affiche alors les identifiants de démonstration
    return {"status": "ok", "demo": settings.DEMO_MODE}
