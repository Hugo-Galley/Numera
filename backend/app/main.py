import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.controllers.systeme.auth import router as auth_router
from app.controllers.systeme.passkeys import router as passkeys_router
from app.controllers.systeme.totp import router as totp_router
from app.controllers.comptes.accounts import router as accounts_router
from app.controllers.analytics import router as analytics_router
from app.controllers.systeme.admin import router as admin_router
from app.controllers.comptes.balance_snapshots import router as balance_snapshots_router
from app.controllers.budget.categories import router as categories_router
from app.controllers.budget.exports import router as exports_router
from app.controllers.systeme.health import router as health_router
from app.controllers.budget.imports import router as imports_router
from app.controllers.investissement.investment_transactions import router as investment_transactions_router
from app.controllers.budget.transactions import router as transactions_router
from app.controllers.budget.recurring_transactions import router as recurring_transactions_router
from app.controllers.systeme.logos import router as logos_router, public_router as logos_public_router
from app.controllers.budget.savings_goals import router as savings_goals_router
from app.controllers.budget.categorization_rules import router as categorization_rules_router
from app.controllers.budget.merchants import router as merchants_router
from app.controllers.budget.tags import router as tags_router
from app.controllers.budget.salary import router as salary_router
from app.controllers.investissement.market import router as market_router
from app.controllers.investissement.etf_profiles import router as etf_profiles_router
from app.controllers.investissement.holdings import router as holdings_router
from app.controllers.investissement.tax import router as tax_router
from app.controllers.budget.transfer_rules import router as transfer_rules_router
from app.controllers.budget.reimbursements import router as reimbursements_router
from app.controllers.budget.month_review import router as month_review_router
from app.controllers.budget.provisions import router as provisions_router
from app.controllers.budget.benefits import router as benefits_router
from app.controllers.comptes.financial_events import router as financial_events_router
from app.controllers.comptes.loans import router as loans_router
from app.controllers.systeme.notifications import router as notifications_router
from app.controllers.analytics.diversity import router as diversity_router
from app.controllers.deps import get_current_user
from app.core.config import settings
from app.integrations.currency import CurrencyConversionError
from app.core.errors import DomainError
from app.services.systeme.demo import ensure_demo_data, is_blocked_in_demo
from app.core.migrations import run_migrations
from app.services.systeme.seeds import seed_all
from app.db.session import SessionLocal
from app.core.logging import setup_logging, get_logger
from app.services.investissement.etf_profiles import refresh_held_etf_profiles
from app.services.systeme.notifications import run_notifications
from app.services.investissement.market.quotes import refresh_held_prices
from app.services.budget.recurring import generate_recurring_transactions
from app.services.budget.salary_generation import check_and_generate_pending_salaries
from app import models  # noqa: F401

# Initialize logging
setup_logging()
logger = get_logger(__name__)


async def recurring_transactions_task():
    """Background task to generate recurring transactions periodically."""
    # Wait a bit after startup to avoid interfering with migrations/seeding
    await asyncio.sleep(10)
    logger.info("Starting recurring transactions background task")
    while True:
        try:
            db = SessionLocal()
            try:
                if settings.DEMO_MODE:
                    # Démo publique : régénération quotidienne, ni cours réels ni notifications
                    await ensure_demo_data(db)
                else:
                    await generate_recurring_transactions(db)
                    check_and_generate_pending_salaries(db)
                    # Cours des titres détenus enregistrés en base (historique de valorisation)
                    await refresh_held_prices(db)
                    # Composition des ETF détenus (Yahoo), au plus une fois par semaine et par profil
                    await refresh_held_etf_profiles(db)
                    # Alertes du Centre d'Actions et résumé hebdo vers ntfy / Telegram (si activés)
                    await run_notifications(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in recurring transactions task: {e}")
        
        # Run every hour
        await asyncio.sleep(3600)


def _log_foreign_key_violations() -> None:
    """Signale les lignes orphelines (FK non respectées) héritées de l'époque où SQLite ignorait les FK."""
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import text
    with SessionLocal() as session:
        violations = session.execute(text("PRAGMA foreign_key_check")).fetchall()
    if violations:
        tables = sorted({row[0] for row in violations})
        logger.warning(f"{len(violations)} foreign key violation(s) found in tables: {', '.join(tables)}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("DEBUG: Lifespan starting...")
    background_task = None
    if settings.app_env != "test":
        logger.info("Running database migrations...")
        run_migrations()  # lève en cas d'échec : mieux vaut ne pas démarrer qu'avec un schéma cassé
        _log_foreign_key_violations()

    if settings.app_env != "test":
        logger.info("DEBUG: Opening database session for seeding...")
        db = SessionLocal()
        try:
            logger.info("DEBUG: Seeding database (categories, ETF presets)...")
            seed_all(db)
            if settings.DEMO_MODE:
                await ensure_demo_data(db)
            logger.info("DEBUG: Seeding completed.")
        finally:
            db.close()
        
        logger.info("DEBUG: Starting background task...")
        background_task = asyncio.create_task(recurring_transactions_task())
    
    logger.info("DEBUG: Lifespan setup complete. Yielding...")
    yield

    if background_task:
        # Référence conservée + arrêt propre (sinon la tâche peut être collectée ou survivre à l'arrêt)
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass



def docs_kwargs(app_env: str) -> dict:
    """En production, ni Swagger ni ReDoc ni le schéma OpenAPI ne sont servis (surface inutile et bavarde)."""
    if app_env == "prod":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


app = FastAPI(title=settings.app_name, lifespan=lifespan, **docs_kwargs(settings.app_env))


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_content())


@app.exception_handler(CurrencyConversionError)
async def currency_conversion_error_handler(_: Request, exc: CurrencyConversionError):
    # Mieux vaut refuser l'opération qu'enregistrer un montant converti au taux 1:1
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    # `input`/`ctx` retirés : une valeur Infinity/NaN fautive rendrait la réponse 422 non sérialisable
    errors = [{k: v for k, v in err.items() if k not in ("input", "ctx")} for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    # FK inexistante, NOT NULL, unicité : une entrée invalide, pas une panne serveur (audit R6/B7)
    logger.warning("IntegrityError: %s", exc.orig)
    return JSONResponse(status_code=422, content={"detail": "Données invalides ou référence inexistante"})


@app.exception_handler(OverflowError)
async def overflow_error_handler(_: Request, exc: OverflowError):
    return JSONResponse(status_code=422, content={"detail": "Valeur numérique hors limites"})


@app.middleware("http")
async def demo_guard(request: Request, call_next):
    if settings.DEMO_MODE and is_blocked_in_demo(request.method, request.url.path):
        # 403 avec un détail métier : le client n'y voit pas une session expirée (cf. lib/api.ts)
        return JSONResponse(status_code=403, content={"detail": "Action désactivée sur l'instance de démonstration"})
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        # Don't log health check to keep logs clean unless they fail
        if request.url.path == "/health" and response.status_code == 200:
            return response
            
        logger.info(
            f"method={request.method} path={request.url.path} "
            f"status={response.status_code} duration={process_time:.2f}ms"
        )
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"method={request.method} path={request.url.path} "
            f"error={str(e)} duration={process_time:.2f}ms", 
            exc_info=True
        )
        # Réponse JSON ici (sous CORSMiddleware) : un 500 laissé à Starlette n'aurait pas
        # d'en-têtes CORS et le navigateur le présenterait comme une erreur réseau (audit R5).
        return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(passkeys_router)
app.include_router(totp_router)
app.include_router(logos_public_router)  # <img> ne peut pas envoyer le JWT : lecture seule, références validées

# Protected routers
protected_routers = [
    accounts_router,
    categories_router,
    transactions_router,
    recurring_transactions_router,
    imports_router,
    analytics_router,
    investment_transactions_router,
    balance_snapshots_router,
    savings_goals_router,
    categorization_rules_router,
    merchants_router,
    tags_router,
    exports_router,
    admin_router,
    salary_router,
    market_router,
    etf_profiles_router,
    holdings_router,
    diversity_router,
    tax_router,
    transfer_rules_router,
    reimbursements_router,
    month_review_router,
    logos_router,
    provisions_router,
    benefits_router,
    financial_events_router,
    loans_router,
    notifications_router,
]

for router in protected_routers:
    app.include_router(router, dependencies=[Depends(get_current_user)])
