from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("", response_model=list[TagRead])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.name.asc()).all()

@router.post("", response_model=TagRead, status_code=201)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    existing = db.query(Tag).filter(Tag.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag name already exists")
    
    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = db.query(Tag).filter(Tag.name == update_data["name"], Tag.id != tag_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tag name already exists")
            
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    db.commit()
    db.refresh(tag)
    return tag

@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    db.delete(tag)
    db.commit()
    return
