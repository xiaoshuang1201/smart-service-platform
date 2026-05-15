# SmartService v2.0 — Enterprise Architecture

| 属性 | 值 |
|------|-----|
| 版本 | v2.0 Enterprise |
| 更新日期 | 2026-05-15 |

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Ingress (TLS 1.3)                         │
│              nginx-ingress / APISIX (auth / rate-limit / WAF)    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────────┐
    │                          │                              │
    ▼                          ▼                              ▼
┌──────────┐          ┌──────────────┐              ┌──────────────┐
│Streamlit │          │  FastAPI     │              │  Celery      │
│  UI Pod  │          │  API Pods    │              │  Worker Pods │
│ (x2)     │───────→  │  (x3→10 HPA) │              │  (x2→8 HPA)  │
└──────────┘          └──────┬───────┘              └──────┬───────┘
                             │                             │
          ┌──────────────────┼───────────────┐             │
          │                  │               │             │
          ▼                  ▼               ▼             │
┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│   Qdrant     │  │  PostgreSQL  │  │ Redis Cluster│◄─────┘
│ (gRPC, 6334) │  │  (主从)      │  │ (Sentinel)   │
│ Vector Store │  │ 会话/消息/用户│  │ 状态+队列    │
└──────────────┘  └──────────────┘  └──────────────┘
                                                  │
          ┌───────────────────────┐               │
          │       MinIO/S3        │               │
          │  (文档存储, Bucket)    │               │
          └───────────────────────┘               │
                                                  │
          ┌───────────────────────┐               │
          │  Observability Stack  │◄──────────────┘
          │ OTel → Prom → Grafana │
          │ (metrics / traces)    │
          └───────────────────────┘
```

## 2. 技术栈 (v2.0)

| 层级 | v1.0 | v2.0 Enterprise | 变更说明 |
|------|------|-----------------|----------|
| Agent 框架 | LangGraph | LangGraph + PostgresSaver | 状态可恢复 |
| LLM | Qwen-Max | Qwen-Max | 不变 |
| 向量数据库 | ChromaDB (embedded) | Qdrant (distributed, gRPC) | 高可用共享存储 |
| 嵌入模型 | text-embedding-v3 | text-embedding-v3 | 不变 |
| 后端 | FastAPI | FastAPI + Gunicorn/Uvicorn Workers | 多 worker 生产化 |
| 前端 | Streamlit | Streamlit (K8s Deployment) | 多副本 |
| 数据库 | - (配置未使用) | PostgreSQL 16 (主从) | ORM 持久化 |
| 缓存/状态 | In-memory dict | Redis (Sentinel/Cluster) | 分布式状态 |
| 文档存储 | 本地目录 | MinIO (S3-compatible) | 对象存储 |
| 异步任务 | - | Celery + Redis | 知识库索引/日志处理 |
| 容器化 | Docker Compose | Kubernetes (k8s/) | 一键部署 |
| 网关 | - | APISIX / nginx-ingress | 认证/限流/WAF |
| 日志 | print + logging | loguru (JSON structured) | 结构化日志 |
| 追踪 | - | OpenTelemetry (OTLP) | 全链路追踪 |
| 指标 | - | Prometheus + Grafana | 可观测性 |
| 告警 | - | AlertManager rules | P99延迟/错误率 |
| 安全 | API Key | API Key + PII脱敏 + 输入守卫 + NetworkPolicy + TLS | 纵深防御 |
| CI/CD | - | GitHub Actions | PR测试 + 自动部署 |
| 测试 | pytest (3文件) | pytest (15+文件) + k6 | 单元/集成/负载 |

## 3. 数据流

```
┌────────────────────────────────────────────────────────────────────┐
│                        同步请求路径                                  │
│                                                                    │
│ User → Ingress(TLS) → APISIX(限流/认证) → FastAPI → InputGuard     │
│   → IntentAgent → [KnowledgeAgent (Qdrant) | ActionAgent (OMS/CRM)]│
│   → CheckConfidence → Response (SSE)                               │
│   → Memory (Redis) + DB (PostgreSQL async)                         │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                        异步任务路径                                  │
│                                                                    │
│ Upload API → MinIO (存储文档) → Celery Worker                       │
│   → chunk + embed → Qdrant (索引) → PostgreSQL (metadata update)    │
│                                                                    │
│ Chat Complete → Celery Task → PostgreSQL (消息持久化)               │
│                                                                    │
│ Cron: cleanup_expired_sessions (清理过期 Redis 会话)                │
└────────────────────────────────────────────────────────────────────┘
```

## 4. 核心组件

### 4.1 Agent 编排 (src/workflow/graph.py)
- LangGraph StateGraph → PostgresSaver 持久化检查点
- 5个节点: intent_classify → route_by_intent → knowledge_rag/action_tools/human_handoff → check_confidence → 输出

### 4.2 向量存储 (src/vector_store/)
- `BaseVectorStore` 抽象接口
- `QdrantVectorStore`: gRPC通信, HNSW索引, Scalar量化
- `VectorStore` ChromaDB 包装 (向后兼容)

### 4.3 业务适配器 (src/business/)
- `OMSAdapter`: 订单系统 (mock/custom HTTP + retry + circuit breaker)
- `CRMAdapter`: 会员系统 (mock/custom HTTP + phone hashing + PII masking)
- `resilience.py`: tenacity retry + pybreaker circuit breaker + timeout + fallback

### 4.4 安全模块 (src/security/)
- `InputGuard`: 提示注入检测 (10+ patterns) + 零宽字符 + Unicode同形字
- `PIIMasker`: 手机号/邮箱/身份证/银行卡脱敏
- `RateLimitMiddleware`: Redis滑动窗口 (含内存兜底)

### 4.5 可观测性 (src/observability/)
- `logging.py`: loguru JSON格式 + trace_id注入
- `tracing.py`: OpenTelemetry (OTLP gRPC export, FastAPI auto-instrument)
- `metrics.py`: Prometheus 指标 (请求数/延迟/Token/工具调用/熔断/活跃会话)

## 5. Kubernetes 部署

```bash
kubectl apply -k k8s/overlays/production/
```

| 资源 | 副本数 | HPA | 说明 |
|------|--------|-----|------|
| smartservice-api | 3→20 | CPU 70% | FastAPI 后端 |
| smartservice-worker | 2→8 | CPU 70% | Celery 异步任务 |
| smartservice-ui | 2 | - | Streamlit 前端 |

所有 Pod 配置了 `livenessProbe`, `readinessProbe`, `securityContext (non-root)`, `resource limits/requests`, `NetworkPolicy`。

## 6. PostgreSQL 数据模型

- `users` (external_id, phone_hashed, email_hashed)
- `conversations` (user_id FK, status, intent, sentiment, metadata JSONB)
- `messages` (conversation_id FK, role, content, trace JSONB, token_count, latency_ms)
- `documents` (filename, file_type, minio_path, status, chunk_count)
- `tool_calls` (message_id FK, tool_name, input_params/output_result JSONB, status, latency_ms)

## 7. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/send` | SSE 流式对话 |
| POST | `/api/v1/chat/send-sync` | 同步对话 |
| POST | `/api/v1/knowledge/upload` | 上传文档 (→MinIO + Celery) |
| GET  | `/api/v1/knowledge/health` | 知识库健康检查 |
| GET  | `/api/v1/admin/health` | 服务健康 |
| GET  | `/api/v1/admin/stats` | 运营统计 |
| GET  | `/metrics` | Prometheus 指标 |
| GET  | `/healthz` | K8s liveness probe |
| GET  | `/readyz` | K8s readiness probe |

## 8. 安全架构

| 层面 | 措施 |
|------|------|
| 传输 | TLS 1.3 (Ingress + cert-manager) |
| API | API Key Header 验证 |
| 网络 | K8s NetworkPolicy (最小权限通信) |
| 数据 | PIIMasker (手机/邮箱/身份证/银行卡脱敏) |
| 输入 | InputGuard (提示注入 + 零宽字符 + 同形字检测) |
| 速率 | Redis 滑动窗口限流 (60 req/min) |
| 审计 | 工具调用/Trace 写入 PostgreSQL 不可篡改 |
| 密钥 | K8s Secrets + External Secrets Operator (生产) |
| CI    | pip-audit + bandit + trivy 容器扫描 |
