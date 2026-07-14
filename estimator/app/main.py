import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging import configure_logging
from app.embedding_pipeline.router import router as embeddings_router
from app.embedding_pipeline.search_router import router as search_router
from app.routers import estimations, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    configure_logging()
    log = structlog.get_logger()
    settings = get_settings()
    log.info("application_started", environment=settings.APP_ENV)
    yield
    log.info("application_shutdown")


app = FastAPI(
    title="Software Estimation CAG Service",
    description="AI-powered software estimation service using Cache Augmented Generation architecture",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(estimations.router)
app.include_router(sessions.router)
app.include_router(embeddings_router)
app.include_router(search_router)


@app.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }
