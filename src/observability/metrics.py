"Prometheus 指标暴露"

from __future__ import annotations
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


chat_request_total = Counter(
    "smartservice_chat_request_total",
    "Total chat requests",
    ["intent", "status"],
)

chat_request_duration_seconds = Histogram(
    "smartservice_chat_request_duration_seconds",
    "Chat request latency",
    ["intent"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_call_duration_seconds = Histogram(
    "smartservice_llm_call_duration_seconds",
    "LLM call latency",
    ["agent_name", "model"],
    buckets=[0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

llm_token_usage_total = Counter(
    "smartservice_llm_token_usage_total",
    "LLM token usage",
    ["agent_name", "type"],
)

rag_retrieval_duration_seconds = Histogram(
    "smartservice_rag_retrieval_duration_seconds",
    "RAG retrieval latency",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
)

tool_call_duration_seconds = Histogram(
    "smartservice_tool_call_duration_seconds",
    "Tool call latency",
    ["tool_name", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0],
)

tool_call_total = Counter(
    "smartservice_tool_call_total",
    "Total tool calls",
    ["tool_name", "status"],
)

circuit_breaker_state = Gauge(
    "smartservice_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half-open, 2=open)",
    ["adapter_name"],
)

active_sessions = Gauge(
    "smartservice_active_sessions",
    "Active conversation sessions",
)

rate_limit_hits_total = Counter(
    "smartservice_rate_limit_hits_total",
    "Rate limit hits",
    ["endpoint"],
)

input_guard_blocks_total = Counter(
    "smartservice_input_guard_blocks_total",
    "Input guard blocks",
    ["reason"],
)


def get_metrics_response() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
