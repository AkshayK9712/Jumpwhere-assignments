import logging
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.request")

API_VERSION = "1"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID / X-API-Version, logs every request, and turns crashes into clean 500s."""

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error rid=%s %s %s", request_id, request.method, request.url.path)
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-API-Version"] = API_VERSION

        level = logging.DEBUG if request.url.path.startswith(("/health", "/api/v1/health")) else logging.INFO
        logger.log(level, "%s %s -> %s (%.1f ms) rid=%s", request.method, request.url.path,
                   response.status_code, duration_ms, request_id)
        return response
