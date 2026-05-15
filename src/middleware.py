"限流中间件 — Redis 滑动窗口 + 内存兜底"

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from src.config import config
from src.observability.metrics import rate_limit_hits_total


class InMemoryRateLimiter:
    def __init__(self):
        self._window: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int) -> bool:
        now = time.time()
        window_start = now - 60
        self._window[key] = [t for t in self._window[key] if t > window_start]
        if len(self._window[key]) >= limit:
            return False
        self._window[key].append(now)
        return True


class RedisRateLimiter:
    def __init__(self):
        self._redis = None
        self._connected = False

    async def _ensure_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from src.memory.redis_memory import _build_redis
            self._redis = _build_redis()
            await self._redis.ping()
            self._connected = True
        except Exception:
            self._connected = False
            self._redis = None
        return self._redis

    async def check(self, key: str, limit: int) -> bool:
        redis = await self._ensure_redis()
        if redis is None:
            return True  # Allow if Redis unavailable
        now_ms = int(time.time() * 1000)
        window_ms = 60000
        pipeline = redis.pipeline()
        pipeline.zremrangebyscore(key, 0, now_ms - window_ms)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(now_ms): now_ms})
        pipeline.expire(key, 60)
        _, count, _, _ = await pipeline.execute()
        return count < limit


_rate_limiter: InMemoryRateLimiter | RedisRateLimiter | None = None


def get_rate_limiter():
    global _rate_limiter
    if _rate_limiter is None:
        if config.security.rate_limit_redis_backend:
            _rate_limiter = RedisRateLimiter()
        else:
            _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path in ("/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        limit = config.security.rate_limit_per_minute

        limiter = get_rate_limiter()

        if isinstance(limiter, InMemoryRateLimiter):
            allowed = limiter.check(client_ip, limit)
        else:
            allowed = await limiter.check(f"rate_limit:{client_ip}", limit)

        if not allowed:
            rate_limit_hits_total.labels(endpoint=path).inc()
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "请求过于频繁，请稍后再试"},
            )

        return await call_next(request)
