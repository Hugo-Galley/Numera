from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import notifications
from app.db.session import get_db
from app.schemas.notification import (
    NotificationSettingsRead,
    NotificationSettingsUpdate,
    NotificationTestRequest,
    NotificationTestResult,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _read(settings: notifications.NotificationSettings) -> NotificationSettingsRead:
    data = asdict(settings)
    for field in notifications.SECRET_FIELDS:
        data[field] = notifications.mask_secret(data[field])
    return NotificationSettingsRead(**data)


@router.get("/settings", response_model=NotificationSettingsRead)
def get_notification_settings(db: Session = Depends(get_db)):
    return _read(notifications.load_settings(db))


@router.put("/settings", response_model=NotificationSettingsRead)
def update_notification_settings(payload: NotificationSettingsUpdate, db: Session = Depends(get_db)):
    return _read(notifications.save_settings(db, payload.model_dump(exclude_unset=True)))


@router.post("/test", response_model=NotificationTestResult)
async def send_test_notification(payload: NotificationTestRequest, db: Session = Depends(get_db)):
    """Message d'essai sur un canal configuré, même désactivé (pour valider les réglages avant de l'activer)."""
    channel = notifications.build_channel(db, payload.channel)
    if channel is None:
        raise HTTPException(status_code=400, detail="Canal incomplet : renseignez ses paramètres puis enregistrez.")
    delivered = await notifications.send_all([channel], "Test Numera", "Les notifications fonctionnent.", "default")
    if not delivered:
        raise HTTPException(status_code=502, detail="Envoi impossible : vérifiez l'adresse, le sujet ou le jeton.")
    return NotificationTestResult(channel=payload.channel, delivered=True)
