from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.portfolio import PortfolioOverview, PortfolioRead
from app.services.analytics import portfolio as portfolio_service

router = APIRouter()


@router.get("/portfolio", response_model=PortfolioOverview)
async def portfolio_overview(db: Session = Depends(get_db)):
    """Somme des comptes titres valorisés par positions : valeur, plus-values latente/réalisée, dividendes, XIRR."""
    return await portfolio_service.portfolio_overview(db)


@router.get("/portfolio/{account_id}", response_model=PortfolioRead)
async def portfolio_account(account_id: int, db: Session = Depends(get_db)):
    """Valeur calculée (positions × cours + espèces), plus-values, XIRR/TWR, courbe reconstituée et rapprochement."""
    return await portfolio_service.portfolio_account(db, account_id)
