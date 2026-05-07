# SmartService Platform — 配置中心
#
# 设计原则: 所有可变参数都通过环境变量注入，不硬编码
# 调试的时候把 DEBUG=true 设上，LLM 调用会打日志
#
# 几个关键参数说明 (都是凭经验设的，没做系统调优):
#   - temperature=0.1: Agent 场景要稳定输出，不能太放飞
#   - chunk_size=800, overlap=150: 试了几组值，这组对中文文档效果最好
#   - bm25_weight=0.3: 混合检索中 BM25 的权重，拍脑袋的，后面要跑消融实验
#   - confidence_threshold=0.7: 低于这个分就转人工，还没用真实数据标定过

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class LLMConfig:
    """LLM 模型配置"""
    provider: str = "dashscope"  # dashscope | openai | deepseek
    model: str = "qwen-max"
    api_key: str = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ))
    temperature: float = 0.1  # Agent 场景用低温度保证输出稳定
    max_tokens: int = 2048
    timeout: int = 30  # 秒

@dataclass
class EmbeddingConfig:
    """Embedding 模型配置"""
    provider: str = "dashscope"
    model: str = "text-embedding-v3"
    api_key: str = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    dimension: int = 1024
    batch_size: int = 20  # 批量 embedding 的大小

@dataclass
class VectorDBConfig:
    """向量数据库配置"""
    backend: str = "chromadb"
    persist_directory: str = "./data/chromadb"
    collection_name: str = "knowledge_base"
    distance_metric: str = "cosine"

@dataclass
class RAGConfig:
    """RAG 检索配置"""
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 5  # 检索返回的文档片段数
    similarity_threshold: float = 0.65  # 相似度阈值，低于此值的结果丢弃
    reranker_enabled: bool = True
    hybrid_search_enabled: bool = True  # 向量 + BM25 混合检索
    bm25_weight: float = 0.3  # BM25 在混合检索中的权重

@dataclass
class AgentConfig:
    """Agent 通用配置"""
    max_iterations: int = 5  # Agent 最大推理循环次数，防止死循环
    max_tool_calls_per_turn: int = 3  # 单回合最大工具调用数
    confidence_threshold: float = 0.7  # 低于此阈值触发人工转接
    human_escalation_trigger_words: list = field(default_factory=lambda: [
        "投诉", "退款", "赔偿", "欺诈", "法律", "律师"
    ])

@dataclass
class MemoryConfig:
    """记忆系统配置"""
    window_size: int = 10  # 保留最近 N 轮对话
    summary_threshold: int = 15  # 超过此轮数自动压缩
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    session_ttl: int = 3600  # 会话过期时间(秒)

@dataclass
class AppConfig:
    """应用全局配置"""
    app_name: str = "SmartService"
    version: str = "1.0.0"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # PostgreSQL
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/smartservice"
    ))
    database_url_sync: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL_SYNC", "postgresql://postgres:postgres@localhost:5432/smartservice"
    ))

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key_header: str = "X-API-Key"
    cors_origins: list = field(default_factory=lambda: ["*"])

    # Rate Limiting
    rate_limit_per_minute: int = 20

    # 子配置
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)

# 全局单例
config = AppConfig()
