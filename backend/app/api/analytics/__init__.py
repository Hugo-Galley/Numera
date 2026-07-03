from fastapi import APIRouter
from .audit import router as audit_router
from .budget import router as budget_router
from .investments import router as investments_router
from .insights import router as insights_router
from .subscriptions import router as subscriptions_router
from .reports import router as reports_router
from .metrics import router as metrics_router

router = APIRouter(prefix="/analytics", tags=["analytics"])
router.include_router(audit_router)
router.include_router(budget_router)
router.include_router(investments_router)
router.include_router(insights_router)
router.include_router(subscriptions_router)
router.include_router(reports_router)
router.include_router(metrics_router)
