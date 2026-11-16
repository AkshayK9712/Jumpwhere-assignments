import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.core.scheduler import scheduler_loop
from app.db.session import SessionLocal

setup_logging()

# Windows can map .js to text/plain, which browsers refuse for ES modules
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("IoT Monitor API started (env=%s, email=%s)", settings.ENVIRONMENT, settings.EMAIL_BACKEND)
    scheduler = None
    if settings.SCHEDULER_ENABLED:
        scheduler = asyncio.create_task(scheduler_loop(SessionLocal, settings.SCHEDULER_INTERVAL_SECONDS))
    yield
    if scheduler is not None:
        scheduler.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler
    logger.info("IoT Monitor API shutting down")


app = FastAPI(
    title="IoT Monitor API",
    description="Centralized API to monitor, control and analyze IoT sensor data across factory locations.",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware order: the LAST one added is the OUTERMOST.
# CORS must be outermost so even 429/500 responses carry CORS headers.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-API-Version", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)

# Versioned API: /api/v1/...  (breaking changes will ship under /api/v2)
app.include_router(api_router, prefix="/api/v1")


# Top-level liveness endpoint (handy for Docker / load balancers)
@app.get("/health", tags=["health"])
def root_health():
    return {"status": "ok"}


# Serve the static frontend at /ui
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/ui", StaticFiles(directory=frontend_dir, html=True), name="frontend")
