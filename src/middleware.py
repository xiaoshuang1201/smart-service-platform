# 简单的滑动窗口限流中间件

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from src.config import config


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于内存滑动窗口的请求限流"""

    def __init__(self, app):
        super().__init__(app)
        self._window: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        # 清理过期记录
        self._window[client_ip] = [t for t in self._window[client_ip] if t > window_start]

        if len(self._window[client_ip]) >= config.rate_limit_per_minute:
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "请求过于频繁，请稍后再试"},
            )

        self._window[client_ip].append(now)
        return await call_next(request)
