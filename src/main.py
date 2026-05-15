# SmartService Platform — FastAPI 入口

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import config
from src.api.routes import router
from src.tools import register_all_tools
from src.middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时：注册所有工具
    register_all_tools()
    print(f" SmartService v{config.version} starting...")
    print(f"   LLM: {config.llm.model}")
    print(f"   VectorDB: {config.vector_db.backend} @ {config.vector_db.persist_directory}")
    print(f"   Docs: http://{config.api_host}:{config.api_port}/docs")
    yield
    # 关闭时：清理资源
    print(" SmartService shutting down...")


app = FastAPI(
    title="SmartService - 智能客服多Agent协同平台",
    version=config.version,
    description="基于 LangGraph 的多Agent智能客服系统",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

# 路由
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )
