from sqlalchemy.orm import Session

from app.core.errors import InvalidOperationError, NotFoundError
from app.models.tag import Tag
from app.repositories.budget import tags as repo
from app.schemas.tag import TagCreate, TagUpdate


def _require(db: Session, tag_id: int) -> Tag:
    tag = repo.get(db, tag_id)
    if not tag:
        raise NotFoundError("Tag not found")
    return tag


def list_tags(db: Session, include_archived: bool) -> list[Tag]:
    return repo.list_all(db, include_archived)


def create_tag(db: Session, payload: TagCreate) -> Tag:
    if repo.name_taken(db, payload.name):
        raise InvalidOperationError("Tag name already exists")
    tag = Tag(**payload.model_dump())
    repo.add(db, tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, payload: TagUpdate) -> Tag:
    tag = _require(db, tag_id)
    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("archived", True) is None:
        update_data.pop("archived")
    if "name" in update_data and repo.name_taken(db, update_data["name"], except_id=tag_id):
        raise InvalidOperationError("Tag name already exists")
    for field, value in update_data.items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    repo.delete(db, _require(db, tag_id))
    db.commit()
