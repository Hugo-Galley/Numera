from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.provision import ProvisionCreate, ProvisionRead, ProvisionSummary, ProvisionUpdate
from app.services import provisions as service

router = APIRouter(prefix="/provisions", tags=["provisions"])


@router.get("", response_model=list[ProvisionRead])
async def list_provisions(db: Session = Depends(get_db)):
    return await service.list_provisions(db)


@router.get("/summary", response_model=ProvisionSummary)
async def provisions_summary(db: Session = Depends(get_db)):
    return await service.provisions_summary(db)


@router.post("", response_model=ProvisionRead, status_code=201)
async def create_provision(payload: ProvisionCreate, db: Session = Depends(get_db)):
    return await service.create_provision(db, payload)


@router.patch("/{provision_id}", response_model=ProvisionRead)
async def update_provision(provision_id: int, payload: ProvisionUpdate, db: Session = Depends(get_db)):
    return await service.update_provision(db, provision_id, payload)


@router.delete("/{provision_id}", status_code=204)
def delete_provision(provision_id: int, db: Session = Depends(get_db)):
    service.delete_provision(db, provision_id)
