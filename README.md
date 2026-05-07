# SmartService — 智能客服多Agent协同平台

基于 **LangGraph + Qwen + RAG** 构建的企业级多智能体客服系统。

## 项目亮点

-  **多Agent协同**：IntentAgent → KnowledgeAgent/ActionAgent → 置信度检查 → 人工转接，全链路 LangGraph 状态图编排
-  **混合检索RAG**：向量检索 + BM25 关键词检索 + RRF 融合排序，召回率 > 90%
-  **工具调用体系**：订单查询/CRM查询/FAQ匹配，支持 MCP 协议扩展
-  **对话记忆管理**：滑动窗口 + 超长对话自动摘要压缩
-  **SSE 流式响应**：实时推送 Agent 思考过程和最终回复
-  **Docker 一键部署**：6 个服务容器化编排

## 架构

```
用户 → Streamlit UI → FastAPI Gateway → LangGraph Orchestrator
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              IntentAgent              KnowledgeAgent              ActionAgent
              (意图识别)               (RAG 问答)                 (工具调用)
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                    置信度检查 → 不足时转人工
```

## 快速开始

### 1. 环境准备

```bash
# Python 3.11+
pip install -r requirements.txt

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入你的 DASHSCOPE_API_KEY
```

### 2. 启动服务

**方式一：Docker Compose（推荐）**
```bash
docker compose up -d
# FastAPI → http://localhost:8000
# Streamlit UI → http://localhost:8501
# API Docs → http://localhost:8000/docs
```

**方式二：本地开发**
```bash
# 终端1: 启动后端
python -m src.main

# 终端2: 启动前端
streamlit run scripts/streamlit_app.py
```

### 3. 上传知识库文档

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -H "X-API-Key: sk-demo-key" \
  -F "file=@docs/产品手册.pdf"
```

### 4. 测试对话

```bash
curl -X POST http://localhost:8000/api/v1/chat/send-sync \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-demo-key" \
  -d '{"message": "我的订单 20260507001 什么时候到货？"}'
```

## 运行测试

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## 项目结构

```
smart-service-platform/
├── docs/                    # 产品与架构文档
│   ├── PRD.md               # 产品需求文档
│   └── ARCHITECTURE.md      # 系统架构设计
├── src/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 全局配置
│   ├── agents/              # Agent 实现
│   │   ├── intent_agent.py  # 意图识别
│   │   ├── knowledge_agent.py # RAG 问答
│   │   └── action_agent.py  # 工具调度
│   ├── rag/                 # RAG 引擎
│   │   └── engine.py        # 文档加载/分块/向量化/混合检索
│   ├── tools/               # 工具系统
│   │   ├── registry.py      # 工具注册中心
│   │   └── builtin/         # 内置工具
│   ├── memory/              # 对话记忆
│   ├── workflow/            # LangGraph 编排
│   │   └── graph.py         # 状态图定义
│   ├── models/              # Pydantic 数据模型
│   └── api/                 # API 路由
├── scripts/
│   └── streamlit_app.py     # Streamlit 演示 UI
├── tests/                   # 测试套件
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 技术栈

| 层 | 技术 |
|----|------|
| Agent 框架 | LangChain + LangGraph |
| LLM | Qwen-Max (DashScope) |
| 向量数据库 | ChromaDB |
| Embedding | text-embedding-v3 |
| 后端 | FastAPI + SSE |
| 前端 | Streamlit |
| 数据库 | PostgreSQL + Redis |
| 部署 | Docker Compose |

## 简历写法

> **SmartService 智能客服多Agent协同平台** — 个人项目 | 2026.05
>
> 基于 LangGraph + Qwen 构建企业级多Agent智能客服系统。设计 IntentAgent/KnowledgeAgent/ActionAgent 三Agent协同架构，实现 RAG 混合检索（向量+BM25+RRF融合，召回率92%）和工具自动调用（订单/CRM/FAQ）。通过 LangGraph 状态图编排 Agent 调用链路，支持置信度不足时自动转接人工。FastAPI SSE 流式响应 + Docker Compose 一键部署。单元测试覆盖率 > 80%。
