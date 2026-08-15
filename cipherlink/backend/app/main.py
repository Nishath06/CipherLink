"""
CipherLink — Main FastAPI Application

Enterprise Encryption-as-a-Service Platform.
"""

import logging
import time
import uuid

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import generate_request_id
from app.db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("cipherlink")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("🔐 CipherLink starting up...")
    # Create tables in dev mode
    if settings.APP_ENV == "development":
        await init_db()
        logger.info("Database tables created (development mode)")
    logger.info(f"CipherLink {settings.APP_VERSION} ready")
    yield
    logger.info("CipherLink shutting down...")


app = FastAPI(
    title="CipherLink API",
    description=(
        "Enterprise Encryption-as-a-Service Platform.\n\n"
        "Provides adaptive hybrid ECC-AES encryption for external applications.\n\n"
        "**Secure Once. Access Everywhere. Integrate Anywhere. Trust Always.**"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)


# ── Request ID Middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    request.state.request_id = request_id

    start_time = time.monotonic()
    response: Response = await call_next(request)
    duration = (time.monotonic() - start_time) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.1f}ms"

    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} "
        f"[{duration:.1f}ms] req={request_id}"
    )
    return response


# ── Security Headers Middleware ───────────────────────────────────────────────

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Global Exception Handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception: {exc} [req={request_id}]")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
            "request_id": request_id,
        },
    )


# ── Register API Routes ──────────────────────────────────────────────────────

from app.api.v1.auth import router as auth_router
from app.api.v1.applications import router as apps_router
from app.api.v1.keys import router as keys_router
from app.api.v1.encryption import router as encryption_router
from app.api.v1.files import router as files_router
from app.api.v1.audit import router as audit_router
from app.api.v1.usage import router as usage_router

from fastapi.staticfiles import StaticFiles
import os

os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="storage")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(apps_router, prefix="/api/v1")
app.include_router(keys_router, prefix="/api/v1")
app.include_router(encryption_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "CipherLink",
        "tagline": "Secure Once. Access Everywhere.",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
