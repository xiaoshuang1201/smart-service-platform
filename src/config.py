# SmartService Platform — 配置中心
# 所有可变参数通过环境变量注入，支持 K8s ConfigMap + Secrets

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    provider: str = "dashscope"
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen-max"))
    api_key: str = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ))
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 30


@dataclass
class EmbeddingConfig:
    provider: str = "dashscope"
    model: str = "text-embedding-v3"
    api_key: str = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    dimension: int = 1024
    batch_size: int = 20


@dataclass
class VectorDBConfig:
    backend: str = field(default_factory=lambda: os.getenv("VECTOR_BACKEND", "chromadb"))
    persist_directory: str = "./data/chromadb"
    collection_name: str = "knowledge_base"
    distance_metric: str = "cosine"
    qdrant_prefer_grpc: bool = True


@dataclass
class QdrantConfig:
    url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333"))
    api_key: str = field(default_factory=lambda: os.getenv("QDRANT_API_KEY", ""))
    grpc_port: int = 6334
    collection_name: str = "knowledge_base"
    vector_size: int = 1024
    hnsw_m: int = 16
    hnsw_ef_construct: int = 200
    quantization: str = "scalar"  # scalar | binary | product | none


@dataclass
class RAGConfig:
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 5
    similarity_threshold: float = 0.65
    reranker_enabled: bool = True
    hybrid_search_enabled: bool = True
    bm25_weight: float = 0.3


@dataclass
class AgentConfig:
    max_iterations: int = 5
    max_tool_calls_per_turn: int = 3
    confidence_threshold: float = 0.7
    human_escalation_trigger_words: list = field(default_factory=lambda: [
        "投诉", "退款", "赔偿", "欺诈", "法律", "律师"
    ])


@dataclass
class MemoryConfig:
    window_size: int = 10
    summary_threshold: int = 15
    session_ttl: int = 3600
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    redis_backend: str = field(default_factory=lambda: os.getenv("REDIS_BACKEND", "single"))
    redis_sentinel_master: str = "mymaster"
    redis_password: str = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))
    redis_fallback_to_memory: bool = True


@dataclass
class CeleryConfig:
    broker_url: str = field(default_factory=lambda: os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"))
    result_backend: str = field(default_factory=lambda: os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"))
    task_default_queue: str = "smartservice"
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1
    task_soft_time_limit: int = 300
    task_time_limit: int = 600


@dataclass
class MinioConfig:
    endpoint: str = field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    access_key: str = field(default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    secret_key: str = field(default_factory=lambda: os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    bucket: str = field(default_factory=lambda: os.getenv("MINIO_BUCKET", "knowledge-docs"))
    secure: bool = field(default_factory=lambda: os.getenv("MINIO_SECURE", "false").lower() == "true")
    region: str = "us-east-1"
    presigned_expiry_seconds: int = 3600


@dataclass
class OMSConfig:
    vendor: str = field(default_factory=lambda: os.getenv("OMS_VENDOR", "mock"))
    base_url: str = field(default_factory=lambda: os.getenv("OMS_BASE_URL", ""))
    api_key: str = field(default_factory=lambda: os.getenv("OMS_API_KEY", ""))
    timeout: int = 10
    max_retries: int = 3
    retry_backoff: float = 1.5
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class CRMConfig:
    vendor: str = field(default_factory=lambda: os.getenv("CRM_VENDOR", "mock"))
    base_url: str = field(default_factory=lambda: os.getenv("CRM_BASE_URL", ""))
    api_key: str = field(default_factory=lambda: os.getenv("CRM_API_KEY", ""))
    timeout: int = 10
    max_retries: int = 3
    retry_backoff: float = 1.5
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class ObservabilityConfig:
    otel_enabled: bool = field(default_factory=lambda: os.getenv("OTEL_ENABLED", "true").lower() == "true")
    otel_exporter_endpoint: str = field(default_factory=lambda: os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    ))
    otel_insecure: bool = True
    otel_service_name: str = "smartservice-api"
    prometheus_enabled: bool = True
    metrics_port: int = 9090


@dataclass
class SecurityConfig:
    api_key_header: str = "X-API-Key"
    api_key: str = field(default_factory=lambda: os.getenv("API_KEY", ""))
    cors_origins: list = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))
    pii_mask_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_redis_backend: bool = True
    input_guard_enabled: bool = True
    input_guard_max_length: int = 4000
    max_upload_size_mb: int = 50


@dataclass
class AppConfig:
    app_name: str = "SmartService"
    version: str = "2.0.0"

    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/smartservice"
    ))
    database_url_sync: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL_SYNC", "postgresql://postgres:postgres@localhost:5432/smartservice"
    ))

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Sub-configs
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    minio: MinioConfig = field(default_factory=MinioConfig)
    oms: OMSConfig = field(default_factory=OMSConfig)
    crm: CRMConfig = field(default_factory=CRMConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Backward-compatible delegating properties
    @property
    def api_key_header(self) -> str:
        return self.security.api_key_header

    @property
    def api_key(self) -> str:
        return self.security.api_key

    @property
    def cors_origins(self) -> list:
        return self.security.cors_origins

    @property
    def rate_limit_per_minute(self) -> int:
        return self.security.rate_limit_per_minute


config = AppConfig()
