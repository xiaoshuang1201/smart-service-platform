"可观测性 — 结构化 JSON 日志 (loguru)"

from __future__ import annotations
import json
import sys
import contextvars
from datetime import datetime, timezone

from loguru import logger as _logger

_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="unknown")


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    return _trace_id_var.get()


def _serialize(record: dict) -> str:
    """JSON 序列化 loguru record"""
    subset = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "trace_id": _trace_id_var.get(),
        "service": "smartservice-api",
        "function": record["function"],
        "line": record["line"],
    }
    if record["exception"]:
        subset["exception"] = str(record["exception"])
    extra = record.get("extra", {})
    if isinstance(extra, dict):
        for k in ("pii_masked", "agent", "elapsed_ms", "tokens"):
            if k in extra:
                subset[k] = extra[k]
    return json.dumps(subset, ensure_ascii=False, default=str) + "\n"


def setup_logging(level: str = "INFO") -> None:
    _logger.remove()
    _logger.add(
        sys.stdout,
        format=_serialize,
        level=level,
        enqueue=True,
    )


logger = _logger
