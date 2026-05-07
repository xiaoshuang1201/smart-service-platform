# SmartService — 系统架构设计文档

| 文档信息 | |
|---------|------|
| 版本 | v1.0 |
| 日期 | 2026-05-07 |

---

## 1. 架构总览

```
                          ┌─────────────────────────┐
                          │     Streamlit UI         │
                          │   (Chat Interface)       │
                          └───────────┬─────────────┘
                                      │ HTTP/SSE
                          ┌───────────▼─────────────┐
                          │    FastAPI Gateway       │
                          │  /api/v1/chat           │
                          │  /api/v1/knowledge      │
                          │  /api/v1/admin          │
                          └───────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
          ┌─────────▼──────┐ ┌───────▼───────┐ ┌───────▼───────┐
          │  Orchestrator  │ │   Memory      │ │  Monitoring   │
          │  (LangGraph)   │ │   Manager     │ │  (LangSmith)  │
          └─────────┬──────┘ └───────────────┘ └───────────────┘
                    │
      ┌─────────────┼─────────────┐
      │             │             │
┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│ Intent    │ │ Knowledge │ │ Action    │
│ Agent     │ │ Agent     │ │ Agent     │
│           │ │ (RAG)     │ │ (Tools)   │
└───────────┘ └─────┬─────┘ └─────┬─────┘
                    │             │
              ┌─────▼─────┐ ┌─────▼─────┐
              │ ChromaDB  │ │ Tool      │
              │ (Vector)  │ │ Registry  │
              └───────────┘ └─────┬─────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
              │ Order API │ │ CRM  API  │ │ FAQ Match │
              │ (Mock)    │ │ (Mock)    │ │ (Local)   │
              └───────────┘ └───────────┘ └───────────┘
```

---

## 2. 技术选型

| 层 | 技术 | 选型理由 |
|----|------|----------|
| **Agent 框架** | LangChain + LangGraph | Agent 编排事实标准，状态图灵活，社区活跃 |
| **LLM** | Qwen-Max (DashScope API) | 中文能力强，价格适中，兼容 OpenAI SDK |
| **向量数据库** | ChromaDB | 轻量级，Python原生，零配置启动 |
| **Embedding** | text-embedding-v3 (DashScope) | 1024维，中文检索效果 SOTA |
| **后端框架** | FastAPI | 异步原生，SSE 流式支持，自动 OpenAPI 文档 |
| **前端** | Streamlit | 快速原型，Python 生态，适合演示 |
| **数据库** | PostgreSQL | 会话记录、知识库元数据持久化 |
| **缓存** | Redis | 会话状态缓存、FAQ 高频问题缓存 |
| **容器化** | Docker Compose | 一键启动 6 个服务 |
| **可观测** | LangSmith (可选) | Agent 调用链可视化追踪 |

---

## 3. 核心流程

### 3.1 一次完整对话流程

```
用户输入 "我的订单 20260507001 什么时候到货？"
  │
  ▼
┌──────────────┐
│ 1. 网关接收   │  FastAPI 验证 API Key, 生成 trace_id
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 2. 意图识别   │  IntentAgent →
│              │  intent = "order_query"
│              │  entities = {order_id: "20260507001"}
│              │  sentiment = "neutral"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 3. 路由分发   │  Orchestrator 根据 intent 决定走 ActionAgent
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 4. 工具调用   │  ActionAgent 识别→调用 order_query(order_id)
│              │  返回: {status:"运输中", eta:"2026-05-09"}
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 5. 结果封装   │  LLM 将工具返回的结构化数据转为自然语言
│              │  "您的订单 20260507001 当前在运输中，预计5月9日送达"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 6. 记忆保存   │  将本轮对话 append 到 session memory
└──────┬───────┘
       │
       ▼
  返回给用户 (SSE 流式)
```

### 3.2 LangGraph 状态图

```python
# 状态图定义
START → intent_classify → route_by_intent
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        knowledge_rag    action_tools    human_handoff
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                       check_confidence
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              confidence > 0.7    confidence <= 0.7
                    │                   │
                    ▼                   ▼
              format_output        human_escalation
                    │                   │
                    └─────────┬─────────┘
                              ▼
                           END
```

---

## 4. 数据库设计

### 4.1 PostgreSQL 表结构

```sql
-- 会话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(128),
    status VARCHAR(32) DEFAULT 'active',  -- active, closed, escalated
    intent VARCHAR(64),
    sentiment VARCHAR(32),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(32) NOT NULL,  -- user, assistant, system, tool
    content TEXT NOT NULL,
    trace JSONB DEFAULT '{}',   -- Agent 调用链信息
    token_count INT DEFAULT 0,
    latency_ms INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

-- 知识库文档元数据表
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(256) NOT NULL,
    file_type VARCHAR(32),
    chunk_count INT DEFAULT 0,
    status VARCHAR(32) DEFAULT 'pending',  -- pending, indexing, ready, failed
    created_at TIMESTAMP DEFAULT now()
);

-- 工具调用记录表 (用于审计和成本分析)
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),
    tool_name VARCHAR(128) NOT NULL,
    input_params JSONB DEFAULT '{}',
    output_result JSONB DEFAULT '{}',
    status VARCHAR(32),  -- success, failed, timeout
    latency_ms INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);
```

### 4.2 ChromaDB Collection 设计

```
collection: knowledge_base
  metadata: { doc_id, chunk_index, filename, section_title }
  embedding: 1024-dim (text-embedding-v3)

collection: faq_cache
  metadata: { question, answer, category, access_count }
  embedding: 1024-dim
```

---

## 5. API 设计 (RESTful)

### 5.1 对话接口

```
POST   /api/v1/chat/send          # 发送消息 (SSE 流式返回)
  Body: { conversation_id?, message, user_id? }
  Response: SSE stream

GET    /api/v1/chat/{conv_id}/history  # 获取会话历史
DELETE /api/v1/chat/{conv_id}          # 结束会话
```

### 5.2 知识库管理接口

```
POST   /api/v1/knowledge/upload       # 上传文档 (multipart/form-data)
GET    /api/v1/knowledge/documents    # 文档列表
DELETE /api/v1/knowledge/documents/{id}  # 删除文档
POST   /api/v1/knowledge/reindex      # 重建索引
GET    /api/v1/knowledge/health       # 知识库健康检查
```

### 5.3 管理接口

```
GET    /api/v1/admin/dashboard        # 运营数据看板
GET    /api/v1/admin/tool-calls       # 工具调用日志
GET    /api/v1/admin/token-usage      # Token 消耗统计
```

---

## 6. 部署架构 (Docker Compose)

```
┌─────────────────────────────────────────────────┐
│                  Docker Network                    │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ FastAPI  │  │ Streamlit│  │  PostgreSQL  │   │
│  │ :8000    │  │ :8501    │  │  :5432       │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ ChromaDB │  │  Redis   │  │  Celery      │   │
│  │ :8001    │  │ :6379    │  │  Worker      │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## 7. 安全设计

| 层面 | 措施 |
|------|------|
| **传输** | API Key Header 验证 |
| **数据** | 手机号/邮箱脱敏（`138****1234`） |
| **LLM** | Prompt 注入防护（对用户输入做语义清洗，拒绝"忽略之前的指令"类注入） |
| **审计** | 所有 Agent 决策和工具调用写入不可篡改日志 |
| **速率** | Redis 实现用户级 Rate Limiting（单用户 20 req/min） |
