# SmartService v2.0 — Enterprise Multi-Agent Customer Service Platform

基于 **LangGraph** 的多 Agent 智能客服系统，支持意图识别、RAG 知识库问答、工具调用、置信度评估与自动转人工。生产级高可用部署。

## 项目概述

SmartService 通过三个专业化 Agent 协作处理客户服务对话：

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| **IntentAgent** | 意图识别 + 实体提取 + 情绪分析 | LLM 解析 + 规则兜底，5种意图分类 |
| **KnowledgeAgent** | 知识库 RAG 问答 | 向量检索 + BM25 混合检索 + RRF 融合排序 |
| **ActionAgent** | 工具调用与结果聚合 | LLM 规划 + 规则兜底，FAQ 关键词匹配 |

**LangGraph** 编排: 意图识别 → 路由分发 → RAG/工具 → 置信度检查 → 低置信度自动转人工。

### v2.0 企业级特性

- **高可用**: K8s Deployment 多副本 + HPA 自动扩缩容 + PodDisruptionBudget
- **可观测性**: loguru JSON 结构化日志 + OpenTelemetry 全链路追踪 + Prometheus 指标 + Grafana 仪表板
- **安全防御**: TLS 1.3 + API Key 鉴权 + PII 脱敏 + 提示注入检测 + NetworkPolicy 最小权限
- **持久化**: PostgreSQL 对话/消息/用户 + Redis 会话记忆(Sentinel/Cluster) + MinIO 文档存储
- **向量数据库**: Qdrant (分布式 gRPC) 替代嵌入式 ChromaDB
- **异步任务**: Celery + Redis 处理知识库索引和日志持久化
- **韧性模式**: 重试 + 熔断 + 超时 + 降级 (tenacity + pybreaker)
- **CI/CD**: GitHub Actions 自动化测试/安全扫描/构建/部署到 K8s

## 快速开始

### 本地开发 (Docker Compose)

```bash
git clone https://github.com/xiaoshuang1201/smart-service-platform.git
cd smart-service-platform
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY
docker compose up -d
# 后端: http://localhost:8000  |  前端: http://localhost:8501  |  API文档: http://localhost:8000/docs
```

### 生产部署 (Kubernetes)

```bash
# 一键部署到 K8s
kubectl apply -k k8s/overlays/staging/    # 预发布环境
kubectl apply -k k8s/overlays/production/ # 生产环境

# 初始化数据库
kubectl exec -n smartservice deployment/smartservice-api -- python scripts/init_db.py

# 验证
curl https://api.smartservice.prod.example.com/api/v1/admin/health
```

详见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/send` | SSE 流式对话 |
| POST | `/api/v1/chat/send-sync` | 同步对话 |
| POST | `/api/v1/knowledge/upload` | 上传文档 (→MinIO + Celery 异步索引) |
| GET  | `/api/v1/knowledge/health` | 知识库健康检查 |
| GET  | `/api/v1/admin/health` | 服务健康 |
| GET  | `/api/v1/admin/stats` | 运营统计 |
| GET  | `/metrics` | Prometheus 指标 |
| GET  | `/healthz` `/readyz` | K8s 探针 |

所有接口（除 `/admin/health`, `/healthz`, `/readyz`, `/metrics`）需在 Header 中携带 `X-API-Key`。

```bash
# SSE 流式对话
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "X-API-Key: sk-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "如何申请退货退款？"}'

# 上传文档
curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -H "X-API-Key: sk-demo-key" \
  -F "file=@product_manual.pdf"
```

## 项目结构

```
smart-service-platform/
├── src/
│   ├── agents/              # 三个 Agent (Intent/Knowledge/Action)
│   ├── rag/                 # RAG 引擎 (文档加载/分块/向量化/混合检索)
│   ├── tools/               # 工具注册中心 + 内置工具 (订单/CRM/FAQ)
│   ├── workflow/            # LangGraph 编排器 (状态图 + 条件路由)
│   ├── memory/              # 对话记忆 (Redis + 内存兜底)
│   ├── models/              # Pydantic 数据模型
│   ├── api/                 # FastAPI 路由 (SSE + 同步 + 知识库)
│   ├── middleware.py         # 限流中间件 (Redis滑动窗口 + 内存兜底)
│   ├── config.py             # 配置中心 (~60+ 环境变量)
│   └── main.py               # FastAPI 入口
│   ├── observability/       # 可观测性 (loguru + OTel + Prometheus)
│   ├── db/                  # PostgreSQL 数据层 (SQLAlchemy ORM)
│   ├── vector_store/        # 向量存储抽象 (ChromaDB/Qdrant)
│   ├── storage/             # MinIO/S3 文档存储
│   ├── business/            # 业务适配器 (OMS/CRM + 韧性模式)
│   ├── queue/               # Celery 异步任务队列
│   └── security/            # 安全模块 (PII脱敏 + 输入守卫)
├── k8s/
│   ├── base/                 # K8s 基础清单 (12个YAML)
│   └── overlays/             # 环境覆盖 (staging/production)
├── prometheus/               # Prometheus 配置
├── grafana/                  # Grafana 仪表板 + 告警规则
├── .github/workflows/        # CI/CD (ci.yml + cd.yml + security-scan.yml)
├── tests/                    # 单元/集成测试
│   ├── load/                 # k6 负载测试脚本
│   └── chaos/                # 混沌工程脚本
├── docs/                     # 架构文档 / 环境变量 / 部署指南
├── scripts/                  # Streamlit前端 / DB初始化 / 迁移脚本
├── Dockerfile                # 后端多阶段构建 (non-root)
├── Dockerfile.ui             # 前端轻量镜像
├── docker-compose.yml        # 本地开发编排
├── requirements.txt          # 完整依赖 (~50个包)
└── .env.example               # 环境变量模板
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph 0.2+ (StateGraph + PostgresSaver) |
| LLM | Qwen-Max (DashScope, OpenAI SDK 兼容) |
| 嵌入模型 | text-embedding-v3 (1024维) |
| 向量数据库 | Qdrant (gRPC, HNSW, scalar quantization) / ChromaDB |
| 后端框架 | FastAPI (async, SSE stream, Gunicorn workers) |
| 数据库 | PostgreSQL 16 (主从, asyncpg) |
| 缓存/状态 | Redis (Sentinel/Cluster) |
| 对象存储 | MinIO (S3-compatible) |
| 异步任务 | Celery + Redis |
| 前端 | Streamlit |
| 可观测性 | loguru → OpenTelemetry → Prometheus → Grafana |
| 容器化 | Docker + Kubernetes |
| 网关 | APISIX / nginx-ingress + cert-manager |
| CI/CD | GitHub Actions |
| 安全 | PII脱敏 + 提示注入检测 + NetworkPolicy + TLS 1.3 |

## 配置

所有配置通过环境变量注入，详见 [docs/ENV_VARS.md](docs/ENV_VARS.md) 和 `.env.example`。

关键参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DASHSCOPE_API_KEY` | - | DashScope API Key (必填) |
| `API_KEY` | - | API 鉴权密钥 (生产必填) |
| `VECTOR_BACKEND` | chromadb | 向量库后端 (chromadb/qdrant) |
| `REDIS_BACKEND` | single | Redis 模式 (single/sentinel/cluster) |
| `OMS_VENDOR` | mock | OMS 后端 (mock/custom) |
| `OTEL_ENABLED` | true | 启用分布式追踪 |
| `LOG_LEVEL` | INFO | 日志级别 |

## 企业级升级记录 (v2.0)

### 高可用
- K8s Deployment + Service + Ingress (TLS 1.3)
- HPA 自动扩缩容 (CPU/Memory, 3→20 replicas)
- PodDisruptionBudget, livenessProbe, readinessProbe
- Redis Sentinel/Cluster 支持 + 内存兜底

### 可观测性
- loguru JSON 结构化日志 (trace_id 全链路注入)
- OpenTelemetry (OTLP gRPC) 自动埋点 FastAPI/LangGraph/SQLAlchemy
- Prometheus 指标: QPS/延迟分位数/Token消耗/熔断状态/活跃会话/限流命中/输入拦截
- Grafana 仪表板 JSON + 7条告警规则

### 持久化
- PostgreSQL ORM (Conversation/Message/Document/ToolCall/User)
- Redis 会话记忆 (分布式, TTL过期)
- MinIO 文档存储 (S3兼容, 预签名URL)
- Celery 异步知识库索引 + 日志处理

### 安全
- PII 自动脱敏 (手机/邮箱/身份证/银行卡) + 日志过滤
- 输入守卫 (10+ 提示注入模式 + 零宽字符 + Unicode同形字)
- NetworkPolicy 最小权限通信
- K8s Secrets + External Secrets Operator
- CI: pip-audit + bandit + trivy 容器扫描

### 业务韧性
- tenacity 指数退避重试 + pybreaker 熔断器
- OMS/CRM 适配器 (mock/custom HTTP, 断路器保护)
- FAQ Redis 热加载 + 内存降级

### CI/CD
- GitHub Actions: PR → lint/test/security-scan
- GitHub Actions: main → docker build/push → deploy to K8s
- Kustomize overlays (staging/production)

### 测试
- 单元测试: agents/memory/tools/db/security/observability
- 集成测试: API 全链路 + Orchestrator 状态图
- 负载测试: k6 (ramp/spike/soak scenarios)
- 混沌工程: pod kill/Redis分区/熔断触发

## 参考

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Qdrant 向量数据库](https://qdrant.tech/documentation/)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [Prometheus 指标最佳实践](https://prometheus.io/docs/practices/naming/)
- [Kubernetes HPA 文档](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)

## License

MIT
