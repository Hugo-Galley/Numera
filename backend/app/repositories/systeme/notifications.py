from sqlalchemy.orm import Session

from app.models.notification_log import NotificationLog


def sent_fingerprints(db: Session) -> set[str]:
    return {row.fingerprint for row in db.query(NotificationLog.fingerprint).all()}
