# SmartService Platform — FastAPI 入口 (v2.0 Enterprise)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from src.config import config
from src.api.routes import router
from src.tools import register_all_tools
from src.middleware import RateLimitMiddleware
from src.observability import setup_logging, set_trace_id
from src.observability.tracing import init_tracing, instrument_fastapi, TraceContextMiddleware
from src.observability.metrics import get_metrics_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(config.log_level)
    init_tracing()
    register_all_tools()
    from src.observability import logger
    logger.info(
        f"SmartService v{config.version} starting",
        agent_model=config.llm.model,
        vector_backend=config.vector_db.backend,
    )
    yield
    logger.info("SmartService shutting down")


app = FastAPI(
    title="SmartService - Enterprise Multi-Agent Customer Service Platform",
    version=config.version,
    description="基于 LangGraph 的多 Agent 智能客服系统 — 企业级生产部署",
    lifespan=lifespan,
)

app.add_middleware(TraceContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(router)
instrument_fastapi(app)


@app.get("/metrics")
async def metrics():
    return get_metrics_response()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready", "version": config.version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )
