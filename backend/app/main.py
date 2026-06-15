import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.accounts import router as accounts_router
from app.api.analytics import router as analytics_router
from app.api.admin import router as admin_router
from app.api.balance_snapshots import router as balance_snapshots_router
from app.api.categories import router as categories_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.investment_transactions import router as investment_transactions_router
from app.api.transactions import router as transactions_router
from app.api.recurring_transactions import router as recurring_transactions_router
from app.api.savings_goals import router as savings_goals_router
from app.api.categorization_rules import router as categorization_rules_router
from app.api.merchants import router as merchants_router
from app.api.tags import router as tags_router
from app.api.salary import router as salary_router
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.seeds import seed_default_categories
from app.db.session import SessionLocal
from app.core.logging import setup_logging, get_logger
from app.core.recurring import generate_recurring_transactions
from app.core.salary import check_and_generate_pending_salaries
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
                await generate_recurring_transactions(db)
                check_and_generate_pending_salaries(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in recurring transactions task: {e}")
        
        # Run every hour
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("DEBUG: Lifespan starting...")
    if settings.app_env != "test":
        logger.info("DEBUG: Starting migrations phase...")
        try:
            run_migrations()
            logger.info("DEBUG: Migrations phase completed.")
        except Exception as e:
            logger.error(f"DEBUG: Migrations failed: {e}", exc_info=True)
    
    if settings.app_env != "test":
        logger.info("DEBUG: Opening database session for seeding...")
        db = SessionLocal()
        try:
            logger.info("DEBUG: Seeding default categories...")
            seed_default_categories(db)
            logger.info("DEBUG: Seeding completed.")
        finally:
            db.close()
        
        logger.info("DEBUG: Starting background task...")
        asyncio.create_task(recurring_transactions_task())
    
    logger.info("DEBUG: Lifespan setup complete. Yielding...")
    yield



app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
        raise e

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)

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
]

for router in protected_routers:
    app.include_router(router, dependencies=[Depends(get_current_user)])
