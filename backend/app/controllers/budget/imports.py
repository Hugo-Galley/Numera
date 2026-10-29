from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.budget import imports as service

router = APIRouter(prefix="/import", tags=["import"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def _read_upload(file: UploadFile) -> bytes:
    """Lit le fichier par blocs et refuse (413) au-delà de MAX_UPLOAD_BYTES, sans tout charger en mémoire."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux (10 Mo maximum)")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/logs")
async def get_import_logs(limit: int = 10, db: Session = Depends(get_db)):
    return service.get_import_logs(db, limit)


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    sample_size: int = Form(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return service.preview_import(db, await _read_upload(file), file.filename, sample_size)


@router.post("/commit")
async def commit_import(
    account_id: int = Form(...),
    file: UploadFile = File(...),
    create_missing_categories: bool = Form(default=True),
    category_mapping: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    return await service.commit_import(
        db, account_id, lambda: _read_upload(file), file.filename, create_missing_categories, category_mapping,
    )
