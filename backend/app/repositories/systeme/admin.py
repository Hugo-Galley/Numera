from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent
from app.models.mcp_token import McpToken


def recent_login_events(db: Session, limit: int) -> list[LoginEvent]:
    return db.query(LoginEvent).order_by(LoginEvent.id.desc()).limit(limit).all()


def mcp_tokens(db: Session) -> list[McpToken]:
    return db.query(McpToken).order_by(McpToken.created_at.desc()).all()


def get_mcp_token(db: Session, token_id: int) -> McpToken | None:
    return db.get(McpToken, token_id)
