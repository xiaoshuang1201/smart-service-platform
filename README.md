# SmartService — 多 Agent 智能客服协同平台

基于 LangGraph 的多 Agent 协同智能客服系统，支持意图识别、RAG 知识库问答、工具调用、置信度评估与自动转人工。

## 项目概述

SmartService 是一个智能客服平台，通过三个专业化 Agent 协作处理客户服务对话：

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| **IntentAgent** | 意图识别 + 实体提取 + 情绪分析 | LLM 解析 + 规则兜底，支持 5 种意图分类 |
| **KnowledgeAgent** | 知识库 RAG 问答 | 向量检索 + BM25 混合检索 + RRF 融合排序 |
| **ActionAgent** | 工具调用与结果聚合 | LLM 规划 + 规则兜底，FAQ 关键词匹配零 LLM 成本 |

**LangGraph** 负责整体编排：意图识别 → 路由分发（RAG / 工具 / 转人工）→ 置信度检查 → 低于阈值自动升级人工。

### 业务场景

典型的电商客服系统，处理：
- 产品使用咨询、退换货政策等 FAQ
- 订单状态查询和物流追踪
- 会员等级、积分、购买历史查询
- 投诉类对话自动识别并转接人工

### 架构图

```
用户消息
  │
  ▼
┌──────────────────────────────────────────────────┐
│                LangGraph 编排器                    │
│                                                    │
│  ┌──────────┐    路由分发     ┌──────────────┐    │
│  │ 意图识别  │ ─────────────→ │ 知识库 RAG   │    │
│  │ Intent   │                │ Knowledge    │    │
│  │ Agent    │                │ Agent        │    │
│  └──────────┘                └──────┬───────┘    │
│       │                             │             │
│       │          ┌──────────┐       │             │
│       └─────────→│ 工具调用  │←──────┘             │
│                  │ Action   │                      │
│                  │ Agent    │                      │
│                  └────┬─────┘                      │
│                       │                            │
│                       ▼                            │
│               ┌──────────────┐                     │
│               │ 置信度检查    │                     │
│               │ Check Conf   │                     │
│               └──┬───────┬───┘                     │
│                  │       │                          │
│          ≥阈值   │       │  <阈值                    │
│                  │       ▼                          │
│                  │  ┌──────────┐                    │
│                  │  │ 转接人工  │                    │
│                  │  │ Handoff  │                    │
│                  │  └──────────┘                    │
│                  ▼                                  │
│            输出回复                                  │
└──────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.11+
- 阿里云 DashScope API Key（[免费申请](https://dashscope.console.aliyun.com/)）

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/xiaoshuang1201/smart-service-platform.git
cd smart-service-platform

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

# 4. 启动后端 (http://localhost:8000)
python -m src.main

# 5. 另开终端，启动前端 (http://localhost:8501)
streamlit run scripts/streamlit_app.py
```

### Docker 部署

```bash
docker compose up -d
```

服务端口：
- FastAPI 后端: `http://localhost:8000`
- API 文档 (Swagger): `http://localhost:8000/docs`
- Streamlit 前端: `http://localhost:8501`

## API 接口

所有接口（除 `/admin/health`）需要在 Header 中携带 `X-API-Key`。

### 对话接口

#### POST `/api/v1/chat/send` — SSE 流式对话

```
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "X-API-Key: sk-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "如何申请退货退款？"}'
```

SSE 事件类型：

| 事件 | 说明 |
|------|------|
| `intent` | 意图识别结果（意图、实体、情绪、置信度） |
| `tool_call` | 工具调用记录（工具名、状态） |
| `token` | 回复文本（8字符分块流式输出） |
| `done` | 完成（包含 session_id、总延迟、token 用量） |
| `error` | 异常（系统错误时的兜底处理） |

#### POST `/api/v1/chat/send-sync` — 同步对话

一次性返回完整结果，适合批量处理和调试。

### 知识库接口

#### POST `/api/v1/knowledge/upload` — 上传文档

支持格式: `.pdf` `.txt` `.md` `.docx` `.csv` `.html`

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -H "X-API-Key: sk-demo-key" \
  -F "file=@product_manual.pdf"
```

响应示例:
```json
{
  "status": "success",
  "filename": "product_manual.pdf",
  "chunk_count": 42,
  "message": "成功索引 42 个文档片段"
}
```

#### GET `/api/v1/knowledge/health` — 知识库健康检查

```json
{
  "total_documents": 0,
  "total_chunks": 128,
  "collection_name": "knowledge_base",
  "status": "healthy"
}
```

### 管理接口

#### GET `/api/v1/admin/health` — 服务健康检查（无需鉴权）

#### GET `/api/v1/admin/stats` — 运营统计

## 项目结构

```
smart-service-platform/
├── src/
│   ├── agents/              # 三个 Agent 实现
│   │   ├── base.py           # 基类：LLM 调用封装 + token 统计
│   │   ├── intent_agent.py   # 意图识别 + 实体提取 + 情绪分析
│   │   ├── knowledge_agent.py # RAG 检索增强问答
│   │   └── action_agent.py   # 工具规划 + 执行 + 结果聚合
│   ├── rag/
│   │   └── engine.py         # 文档加载 / 分块 / 向量化 / ChromaDB / BM25 / 混合检索
│   ├── tools/
│   │   ├── registry.py       # 工具注册中心（Protocol 接口）
│   │   └── builtin/          # 内置工具
│   │       ├── order_query.py # 订单查询（模拟数据）
│   │       ├── crm_lookup.py  # CRM 查询（模拟数据 + PII 脱敏）
│   │       └── faq_match.py   # FAQ 关键词匹配（零 LLM 成本）
│   ├── workflow/
│   │   └── graph.py          # LangGraph 编排器（状态图 + 条件路由）
│   ├── memory/
│   │   └── conversation_memory.py # 滑动窗口 + 摘要压缩的对话记忆
│   ├── models/
│   │   └── schemas.py        # Pydantic 数据模型
│   ├── api/
│   │   └── routes.py         # FastAPI 路由（SSE + 同步 + 知识库 + 管理）
│   ├── middleware.py          # 限流中间件
│   ├── config.py             # 配置中心（环境变量注入）
│   └── main.py               # FastAPI 入口
├── scripts/
│   ├── streamlit_app.py      # Streamlit 演示前端
│   └── tune_bm25_weight.py   # BM25 权重调优脚本
├── tests/
│   ├── conftest.py            # pytest fixtures
│   ├── test_api.py            # API 集成测试
│   ├── test_intent_agent.py   # IntentAgent 单元测试
│   ├── test_knowledge_agent.py # KnowledgeAgent 单元测试
│   ├── test_conversation_memory.py # 记忆系统单元测试
│   └── test_tools.py          # 工具系统测试
├── data/knowledge_base/       # 示例知识库文档
├── docs/
│   ├── ARCHITECTURE.md        # 架构设计文档
│   └── PRD.md                 # 产品需求文档
├── Dockerfile                 # 后端容器镜像
├── Dockerfile.ui              # 前端容器镜像（轻量）
├── docker-compose.yml         # 服务编排
├── requirements.txt           # 完整依赖
├── requirements-ui.txt        # 前端轻量依赖
├── .env.example               # 环境变量模板
├── TODO.md                    # 开发计划
└── DEVLOG.md                  # 开发日志
```

## 配置说明

所有配置通过环境变量注入，详见 `src/config.py`：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DASHSCOPE_API_KEY` | - | 阿里云 DashScope API Key（必填） |
| `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | LLM API 地址 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 连接（暂未使用） |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接（暂未使用） |
| `API_KEY` | `sk-demo-key` | API 鉴权密钥 |
| `DEBUG` | `false` | 开启后 LLM 调用会输出详细日志 |

### 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 800 | 文档分块大小（中文文档优化值） |
| `chunk_overlap` | 150 | 分块重叠量 |
| `top_k` | 5 | RAG 检索返回数 |
| `bm25_weight` | 0.3 | BM25 在混合检索中的权重 |
| `similarity_threshold` | 0.65 | 检索结果最低相似度 |
| `confidence_threshold` | 0.7 | 低于此值触发人工转接 |
| `temperature` | 0.1 | LLM 温度（Agent 场景需稳定输出） |

### BM25 权重调优

```bash
# 运行调优脚本评估不同权重的 MRR 和 Recall@3
python scripts/tune_bm25_weight.py
```

## 技术栈

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| Agent 框架 | LangGraph 0.2+ | 显式状态图，调试清晰，条件路由灵活 |
| LLM | Qwen-Max (DashScope) | 中文效果好，OpenAI SDK 兼容 |
| 嵌入模型 | text-embedding-v3 | 1024 维，DashScope 原生支持 |
| 向量数据库 | ChromaDB 0.5+ | 轻量，Python 原生，单机够用 |
| API 框架 | FastAPI | 异步原生支持，SSE 流式 |
| 数据模型 | Pydantic v2 | 类型安全，自动文档生成 |
| 前端 | Streamlit | 快速原型演示 |
| 容器化 | Docker Compose | 一键部署 |
| 测试 | pytest + pytest-asyncio | 异步测试支持 |

## 优化记录

以下是对 v1.0.0 版本的优化改进：

### 安全加固
- **API Key 鉴权**: 移除硬编码 `sk-demo-key`，改为环境变量 `API_KEY` 注入，支持生产环境自定义密钥
- **限流保护**: 新增 `RateLimitMiddleware` 滑动窗口限流中间件，默认 20 次/分钟，防止接口滥用

### 稳定性提升
- **编排器异常处理**: `run_orchestrator` 新增 try/except，LLM 调用失败时优雅降级返回人工转接提示，不再直接崩溃
- **SSE 流式增强**: 添加 error 事件类型，异常时在前端展示错误提示而非静默失败
- **记忆系统 LLM 摘要**: 新增 `set_llm_summarizer()` 接口，支持注入 LLM 摘要函数自动压缩长对话，失败时自动回退规则摘要

### 代码质量
- **IntentResult 类型统一**: `route_by_intent` 统一使用 Pydantic 对象属性访问，消除 `hasattr`/`.get()` 混用问题
- **移除未使用导入**: 清理 `AsyncSession` 等未使用的数据库导入
- **新增测试覆盖**: 新增 `test_knowledge_agent.py`（RAG 检索 + LLM 生成）、`test_conversation_memory.py`（滑动窗口 + 摘要压缩 + LRU 淘汰），测试文件从 3 个增至 5 个

### 部署优化
- **前端镜像分离**: UI 服务改用独立轻量 `Dockerfile.ui`，仅包含 Streamlit + requests，镜像体积大幅减小
- **BM25 调优工具**: 新增 `scripts/tune_bm25_weight.py`，支持在标注数据上评估不同 BM25 权重的 MRR 和 Recall@3

### 配置改进
- `.env.example` 新增 `API_KEY` 配置项
- Streamlit 前端 API 地址和密钥改为环境变量注入
- 配置文件新增 `api_key` 字段统一管理鉴权密钥

## 开发计划

详见 [TODO.md](TODO.md)：
- **近期**: FAQ 库迁移 Redis、对话记忆 Redis 持久化、LLM 摘要压缩、置信度阈值自动调参
- **中期**: ChromaDB 迁移 Milvus、接入 LangSmith/LangFuse 调用链追踪、前端迁移 React
- **远期**: MCP Server 暴露工具、code-interpreter tool、知识库增量更新、多语言支持

## 参考资源

- [LangGraph 官方文档 - Agent Supervisor](https://langchain-ai.github.io/langgraph/)
- [ChromaDB HNSW 参数调优](https://docs.trychroma.com/usage-guide)
- [RRF (Reciprocal Rank Fusion) 论文](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [DashScope API 文档](https://help.aliyun.com/zh/dashscope/)

## License

MIT
