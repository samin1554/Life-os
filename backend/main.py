"""Life OS FastAPI application."""
import logging
import os
from contextlib import asynccontextmanager

# Fix SSL certificate verification on macOS Python installations
if not os.environ.get("SSL_CERT_FILE"):
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except ImportError:
        pass

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.database import check_db_connection, _get_engine
from core.config import get_settings
from routers import auth, onboarding, tasks, checkin, chat, goals, memory, dashboard, agents, files, notifications, user_settings, uploads, integrations
import redis
import chromadb

settings = get_settings()
logging.basicConfig(level=logging.INFO)

# Rate limiter (keyed by user IP)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("Life OS starting up...")
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        from core.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
    yield
    print("Life OS shutting down...")
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        from core.scheduler import stop_scheduler
        stop_scheduler()
    await _get_engine().dispose()


app = FastAPI(
    title="Life OS API",
    description="AI Life Coach & Executive Function System",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS — use allowed_origins list + always include frontend_url
cors_origins = list(settings.allowed_origins)
if settings.frontend_url and settings.frontend_url not in cors_origins:
    cors_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint — minimal in production, detailed in dev."""
    # In production, return minimal info (no service details)
    if settings.environment == "production":
        try:
            db_ok = await check_db_connection()
            chroma_ok = False
            try:
                from core.memory import get_chroma_client
                get_chroma_client().heartbeat()
                chroma_ok = True
            except Exception:
                pass
            status = "ok" if (db_ok and chroma_ok) else "degraded"
            return {"status": status, "chroma": "ok" if chroma_ok else "disconnected"}
        except Exception:
            return {"status": "degraded"}

    # Development: full service check
    result = {"status": "ok", "services": {}}

    try:
        db_ok = await check_db_connection()
        result["services"]["postgresql"] = "ok" if db_ok else "error"
    except Exception as e:
        result["services"]["postgresql"] = f"error: {str(e)}"

    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        result["services"]["redis"] = "ok"
    except Exception as e:
        result["services"]["redis"] = f"error: {str(e)}"

    try:
        from core.memory import get_chroma_client
        get_chroma_client().heartbeat()
        result["services"]["chroma"] = "ok"
    except Exception as e:
        result["services"]["chroma"] = f"error: {str(e)}"

    if all(v == "ok" for v in result["services"].values()):
        result["status"] = "ok"
    else:
        result["status"] = "degraded"

    return result


# Routers
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(tasks.router)
app.include_router(checkin.router)
app.include_router(chat.router)
app.include_router(goals.router)
app.include_router(memory.router)
app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(files.router)
app.include_router(notifications.router)
app.include_router(user_settings.router)
app.include_router(uploads.router)
app.include_router(integrations.router)


@app.get("/")
async def root():
    return {"message": "Life OS API", "version": "0.1.0"}


