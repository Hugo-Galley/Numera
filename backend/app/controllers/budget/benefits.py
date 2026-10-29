from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.benefit import BenefitCreate, BenefitDeclared, BenefitRead, BenefitSummary, BenefitUpdate
from app.services.budget import benefits as service

router = APIRouter(prefix="/benefits", tags=["benefits"])


@router.get("", response_model=list[BenefitRead])
def list_benefits(db: Session = Depends(get_db)):
    return service.list_benefits(db)


@router.get("/summary", response_model=BenefitSummary)
def benefits_summary(db: Session = Depends(get_db)):
    return service.benefits_summary(db)


@router.post("", response_model=BenefitRead, status_code=201)
def create_benefit(payload: BenefitCreate, db: Session = Depends(get_db)):
    return service.create_benefit(db, payload)


@router.patch("/{benefit_id}", response_model=BenefitRead)
def update_benefit(benefit_id: int, payload: BenefitUpdate, db: Session = Depends(get_db)):
    return service.update_benefit(db, benefit_id, payload)


@router.post("/{benefit_id}/declared", response_model=BenefitRead)
def mark_declared(benefit_id: int, payload: BenefitDeclared, db: Session = Depends(get_db)):
    return service.mark_declared(db, benefit_id, payload)


@router.delete("/{benefit_id}", status_code=204)
def delete_benefit(benefit_id: int, db: Session = Depends(get_db)):
    service.delete_benefit(db, benefit_id)
