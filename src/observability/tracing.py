"OpenTelemetry 分布式追踪"

from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.config import config
from src.observability import set_trace_id


def init_tracing() -> None:
    if not config.observability.otel_enabled:
        return
    resource = Resource.create({
        SERVICE_NAME: config.observability.otel_service_name,
        SERVICE_VERSION: config.version,
    })
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=config.observability.otel_exporter_endpoint,
        insecure=config.observability.otel_insecure,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def get_tracer(name: str = "smartservice"):
    return trace.get_tracer(name)


def instrument_fastapi(app) -> None:
    if config.observability.otel_enabled:
        FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine) -> None:
    if config.observability.otel_enabled:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


class TraceContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id", "") or request.headers.get("traceparent", "")
        if trace_id:
            set_trace_id(trace_id[:32])
        response = await call_next(request)
        if trace_id:
            response.headers["x-trace-id"] = trace_id[:32]
        return response


@asynccontextmanager
async def trace_agent(name: str, **attrs) -> AsyncGenerator:
    tracer = get_tracer()
    with tracer.start_as_current_span(f"agent.{name}") as span:
        for k, v in attrs.items():
            span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise
