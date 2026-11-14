from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services.budget import tags as service

if TYPE_CHECKING:
    from app.models.tag import Tag

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(include_archived: bool = Query(default=True), db: Session = Depends(get_db)) -> "list[Tag]":
    return service.list_tags(db, include_archived)


@router.post("", response_model=TagRead, status_code=201)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)) -> "Tag":
    return service.create_tag(db, payload)


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)) -> "Tag":
    return service.update_tag(db, tag_id, payload)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)) -> None:
    service.delete_tag(db, tag_id)
