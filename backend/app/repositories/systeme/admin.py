from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent
from app.models.mcp_token import McpToken


def recent_login_events(db: Session, limit: int) -> list[LoginEvent]:
    return db.query(LoginEvent).order_by(LoginEvent.id.desc()).limit(limit).all()


def mcp_tokens(db: Session) -> list[McpToken]:
    return db.query(McpToken).order_by(McpToken.created_at.desc()).all()


def get_mcp_token(db: Session, token_id: int) -> McpToken | None:
    return db.get(McpToken, token_id)


def prune_login_events(db: Session, keep: int) -> None:
    """Ne garde que les `keep` connexions les plus récentes."""
    stale = db.query(LoginEvent.id).order_by(LoginEvent.id.desc()).offset(keep).all()
    if stale:
        db.query(LoginEvent).filter(LoginEvent.id.in_([row.id for row in stale])).delete(synchronize_session=False)


def mcp_token_by_hash(db: Session, token_hash: str) -> McpToken | None:
    return db.query(McpToken).filter(McpToken.token_hash == token_hash).first()
