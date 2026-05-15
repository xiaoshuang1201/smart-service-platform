# SmartService 环境变量完整参考

## LLM / Embedding

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DASHSCOPE_API_KEY` | - | 阿里云 DashScope API Key (必填) |
| `LLM_MODEL` | `qwen-max` | LLM 模型名称 |
| `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | LLM API 地址 |

## Database

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/smartservice` | Async 数据库连接 |
| `DATABASE_URL_SYNC` | `postgresql://postgres:postgres@localhost:5432/smartservice` | Sync 数据库连接 |

## Redis

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 URL |
| `REDIS_BACKEND` | `single` | `single` / `sentinel` / `cluster` |
| `REDIS_PASSWORD` | - | Redis 密码 |
| `REDIS_SENTINEL_HOSTS` | `localhost:26379` | Sentinel 地址列表 (逗号分隔) |

## Celery

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery 消息代理 |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery 结果后端 |

## Qdrant

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VECTOR_BACKEND` | `chromadb` | 向量库后端 (`chromadb` / `qdrant`) |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP 地址 |
| `QDRANT_API_KEY` | - | Qdrant API Key |
| `QDRANT_GRPC_PORT` | `6334` | Qdrant gRPC 端口 |

## MinIO

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO/S3 端点 |
| `MINIO_ACCESS_KEY` | `minioadmin` | Access Key |
| `MINIO_SECRET_KEY` | `minioadmin` | Secret Key |
| `MINIO_BUCKET` | `knowledge-docs` | 存储桶名 |
| `MINIO_SECURE` | `false` | 是否使用 HTTPS |

## Business Adapters

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OMS_VENDOR` | `mock` | OMS 后端 (`mock` / `custom`) |
| `OMS_BASE_URL` | - | OMS API 地址 |
| `OMS_API_KEY` | - | OMS API Key |
| `CRM_VENDOR` | `mock` | CRM 后端 (`mock` / `custom`) |
| `CRM_BASE_URL` | - | CRM API 地址 |
| `CRM_API_KEY` | - | CRM API Key |

## Observability

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OTEL_ENABLED` | `true` | 启用 OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP Collector 地址 |

## Security

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `API_KEY` | - | API 鉴权密钥 (生产必填) |
| `CORS_ORIGINS` | `*` | 允许的跨域来源 |

## App

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DEBUG` | `false` | 调试模式 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
