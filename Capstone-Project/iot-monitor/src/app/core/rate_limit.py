"""Simple fixed-window rate limiter (in memory, per process).

For several server workers or machines, swap the dict for Redis; the middleware stays the same.
"""
import threading
import time

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import decode_access_token

AUTH_LIMITED_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/resend-verification",
}


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, int], int] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def hit(self, key: str, limit: int, window: int = 60) -> tuple[bool, int, int]:
        """Count one request. Returns (allowed, remaining, seconds_until_reset)."""
        now = time.time()
        bucket = int(now // window)
        with self._lock:
            if len(self._hits) > 10_000:  # drop old windows
                self._hits = {k: v for k, v in self._hits.items() if k[1] >= bucket}
            count = self._hits.get((key, bucket), 0) + 1
            self._hits[(key, bucket)] = count
        retry_after = max(1, int(window - (now % window)))
        return count <= limit, max(limit - count, 0), retry_after


limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if (
            not settings.RATE_LIMIT_ENABLED
            or request.method == "OPTIONS"
            or not path.startswith("/api/v1/")
            or path.startswith("/api/v1/health")
        ):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        if path in AUTH_LIMITED_PATHS:
            key, limit = f"auth:{ip}", settings.RATE_LIMIT_AUTH_PER_MINUTE
        else:
            key, limit = f"ip:{ip}", settings.RATE_LIMIT_DEFAULT_PER_MINUTE
            header = request.headers.get("authorization", "")
            if header.lower().startswith("bearer "):
                try:  # logged-in users are limited per user, not per IP
                    key = f"user:{decode_access_token(header[7:].strip())['sub']}"
                except Exception:
                    pass

        allowed, remaining, retry_after = limiter.hit(key, limit)
        headers = {"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": str(remaining)}
        if not allowed:
            return JSONResponse(
                {"detail": "Too many requests. Please slow down."},
                status_code=429,
                headers={**headers, "Retry-After": str(retry_after)},
            )
        response = await call_next(request)
        response.headers.update(headers)
        return response
