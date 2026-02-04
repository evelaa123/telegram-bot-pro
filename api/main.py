"""
FastAPI Admin Panel Backend.
Provides REST API for bot administration.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, users, stats, settings as settings_router, tasks
from database import init_db, close_db
from database.redis_client import redis_client
from config import settings
import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Admin API...")
    await init_db()
    await redis_client.connect()
    
    # Create default admin if needed
    from api.services.admin_service import admin_service
    await admin_service.create_default_admin()
    
    logger.info("Admin API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Admin API...")
    await redis_client.close()
    await close_db()
    logger.info("Admin API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Telegram AI Bot Admin API",
        description="Administration panel for Telegram AI Assistant Bot",
        version="1.0.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
    app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    return app


# Create app instance
app = create_app()
