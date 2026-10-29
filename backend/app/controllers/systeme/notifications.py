from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import require_interactive_session
from app.db.session import get_db
from app.schemas.notification import (
    NotificationSettingsRead,
    NotificationSettingsUpdate,
    NotificationTestRequest,
    NotificationTestResult,
)
from app.services.systeme import notifications as service

# Sujet ntfy et chat Telegram permettent d'écrire sur le canal : jamais accessibles avec un token MCP
router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(require_interactive_session)])


@router.get("/settings", response_model=NotificationSettingsRead)
def get_notification_settings(db: Session = Depends(get_db)):
    return service.get_notification_settings(db)


@router.put("/settings", response_model=NotificationSettingsRead)
def update_notification_settings(payload: NotificationSettingsUpdate, db: Session = Depends(get_db)):
    return service.update_notification_settings(db, payload.model_dump(exclude_unset=True))


@router.post("/test", response_model=NotificationTestResult)
async def send_test_notification(payload: NotificationTestRequest, db: Session = Depends(get_db)):
    """Message d'essai sur un canal configuré, même désactivé (pour valider les réglages avant de l'activer)."""
    return await service.send_test_notification(db, payload)
