import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.ai.runs import reap_stuck_runs
from app.core.config import settings
from app.db.session import engine

from app.routers.ai import router as ai_router
from app.routers.agreements import router as agreements_router
from app.routers.auth import router as auth_router
from app.routers.deliverables import router as deliverables_router
from app.routers.evaluations import router as evaluations_router
from app.routers.milestones import router as milestones_router
from app.routers.mock_paypal import router as mock_paypal_router
from app.routers.payments import (
    project_ledger_router,
    router as payments_router,
)
from app.routers.projects import router as projects_router
from app.routers.users import router as users_router
from app.routers.webhooks import router as webhooks_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reaper_scheduler():
    """Periodically recover evaluation runs stuck in RUNNING state."""
    while True:
        try:
            recovered = await asyncio.to_thread(reap_stuck_runs)

            if recovered:
                logger.info(
                    "Evaluation reaper recovered %d stuck runs.",
                    recovered,
                )

        except Exception:
            logger.exception("Evaluation reaper encountered an error.")

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    reaper_task = asyncio.create_task(reaper_scheduler())

    try:
        yield
    finally:
        reaper_task.cancel()

        try:
            await reaper_task
        except asyncio.CancelledError:
            logger.info("Evaluation reaper stopped.")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered milestone project agreements and payment management.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing application routes
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(agreements_router)
app.include_router(milestones_router)
app.include_router(deliverables_router)
app.include_router(evaluations_router)

# Member 2: AI routes
app.include_router(ai_router)

# Existing payment routes
app.include_router(payments_router)
app.include_router(project_ledger_router)
app.include_router(webhooks_router)

if settings.payments_mode.lower() == "mock":
    app.include_router(mock_paypal_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to MilestoneMate AI",
        "status": "running",
    }


@app.get("/api/health")
def health_check():
    database_status = "connected"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "disconnected"

    return {
        "status": "ok" if database_status == "connected" else "degraded",
        "service": settings.app_name,
        "database": database_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }