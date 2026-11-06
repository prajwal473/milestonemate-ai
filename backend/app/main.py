from datetime import datetime, timezone
from app.routers.agreements import router as agreements_router
from app.routers.milestones import router as milestones_router
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.routers.deliverables import router as deliverables_router
from app.core.config import settings
from app.db.session import engine
from app.routers.users import router as users_router
from app.routers.auth import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.evaluations import router as evaluations_router

app = FastAPI(
    title=settings.app_name,
    description="AI-powered milestone project agreements and payment management.",
    version="0.1.0",
)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(agreements_router)
app.include_router(milestones_router)
app.include_router(deliverables_router)
app.include_router(evaluations_router)


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