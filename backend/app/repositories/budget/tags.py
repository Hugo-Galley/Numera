from sqlalchemy.orm import Session

from app.models.tag import Tag


def list_all(db: Session, include_archived: bool) -> list[Tag]:
    query = db.query(Tag)
    if not include_archived:
        query = query.filter(Tag.archived.is_(False))
    return query.order_by(Tag.name.asc()).all()


def get(db: Session, tag_id: int) -> Tag | None:
    return db.query(Tag).filter(Tag.id == tag_id).first()


def name_taken(db: Session, name: str, except_id: int | None = None) -> bool:
    query = db.query(Tag).filter(Tag.name == name)
    if except_id is not None:
        query = query.filter(Tag.id != except_id)
    return query.first() is not None


def add(db: Session, tag: Tag) -> None:
    db.add(tag)
    db.flush()


def delete(db: Session, tag: Tag) -> None:
    db.delete(tag)
