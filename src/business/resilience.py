"韧性模式 — 重试、熔断、超时、降级"

from __future__ import annotations
import asyncio
import functools
from typing import Any, Callable

import pybreaker
import tenacity

from src.observability import logger
from src.observability.metrics import circuit_breaker_state


def with_retry(
    max_attempts: int = 3,
    backoff: float = 1.5,
    exceptions: tuple = (Exception,),
):
    """指数退避重试装饰器"""
    return tenacity.retry(
        stop=tenacity.stop_after_attempt(max_attempts),
        wait=tenacity.wait_exponential(multiplier=backoff, min=0.5, max=10),
        retry=tenacity.retry_if_exception_type(exceptions),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {retry_state.fn.__name__}",
            attempt=retry_state.attempt_number,
        ),
    )


def with_timeout(seconds: int = 10):
    """超时装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        return wrapper
    return decorator


class CircuitBreakerManager:
    """熔断器管理器"""

    def __init__(self):
        self._breakers: dict[str, pybreaker.CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        fail_max: int = 5,
        timeout_duration: int = 60,
    ) -> pybreaker.CircuitBreaker:
        if name not in self._breakers:
            cb = pybreaker.CircuitBreaker(
                fail_max=fail_max,
                timeout_duration=timeout_duration,
                name=name,
            )
            cb._name = name
            # Monitor state changes
            original_open = cb.open

            def _open():
                original_open()
                circuit_breaker_state.labels(adapter_name=name).set(2)
                logger.warning(f"Circuit breaker OPEN: {name}")

            cb._open = _open

            def _on_state_change(new_state):
                mapping = {"closed": 0, "half-open": 1, "open": 2}
                circuit_breaker_state.labels(adapter_name=name).set(
                    mapping.get(new_state, -1)
                )
                logger.info(f"Circuit breaker {new_state}: {name}")

            self._breakers[name] = cb
        return self._breakers[name]


cb_manager = CircuitBreakerManager()


async def resilient_call(
    fn: Callable,
    *args,
    retry_attempts: int = 3,
    backoff: float = 1.5,
    timeout: int = 10,
    circuit_breaker_name: str | None = None,
    fallback_fn: Callable | None = None,
    **kwargs,
) -> Any:
    """韧性调用: 重试 + 熔断 + 超时 + 降级"""
    decorated = with_retry(max_attempts=retry_attempts, backoff=backoff)(
        with_timeout(timeout)(fn)
    )
    if circuit_breaker_name:
        breaker = cb_manager.get_or_create(
            circuit_breaker_name,
            fail_max=retry_attempts,
        )
        try:
            return await breaker.call(decorated, *args, **kwargs)
        except (pybreaker.CircuitBreakerError, Exception) as e:
            if fallback_fn:
                logger.warning(
                    f"Circuit breaker triggered, using fallback",
                    breaker=circuit_breaker_name,
                    error=str(e),
                )
                return await fallback_fn(*args, **kwargs)
            raise
    else:
        try:
            return await decorated(*args, **kwargs)
        except Exception as e:
            if fallback_fn:
                return await fallback_fn(*args, **kwargs)
            raise
