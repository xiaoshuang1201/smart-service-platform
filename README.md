# SmartService — 多Agent客服协同平台

大三下学期自己捣鼓的一个项目，想搞清楚 LangGraph 到底怎么用，顺便把之前学的 RAG 和 Function Calling 串起来。断断续续写了快两周，还有很多可以改进的地方。

## 跑起来

```bash
# 装依赖 (Python 3.11 就行)
pip install -r requirements.txt

# 复制一份 .env，填你自己的 DASHSCOPE_API_KEY
cp .env.example .env

# 启动后端
python -m src.main

# 另开一个终端，启动前端
streamlit run scripts/streamlit_app.py
```

Docker 方式：
```bash
docker compose up -d
# 后端 localhost:8000，前端 localhost:8501
```

## 做了什么

三个 Agent 协作处理客服对话：

- **IntentAgent** — 先搞清楚用户到底想问什么（查订单？问知识？纯抱怨？），顺便把订单号手机号这些实体抽出来。LLM 解析挂了的话有规则兜底
- **KnowledgeAgent** — 从上传的文档里检索相关内容，然后用向量 + BM25 混合检索，RRF 融合排序。检索不到就老实说不知道，不硬编
- **ActionAgent** — 需要查数据的时候动态调工具（订单查询 / CRM / FAQ 匹配），FAQ 匹配不用 LLM，直接关键词匹配，省钱且快

LangGraph 做整体编排，置信度不够的时候自动转人工，不会硬撑着乱回。

## 目前的问题

- 混合检索的 BM25 权重是拍脑袋调的 0.3，没有做系统的消融实验
- ChromaDB 数据量大了以后检索会变慢，后面可能要换 Milvus
- 对话记忆现在是简单的滑动窗口，长对话摘要做的比较糙
- Streamlit 前端是凑合用的，后面打算换成 React，顺便练手
- 异常处理还不够完善，LLM 返回格式不稳定的时候偶尔会崩

## 目录结构

```
src/
├── agents/          # 三个 Agent：intent / knowledge / action
│   └── base.py      # 基类，封装 LLM 调用和 token 统计
├── rag/
│   └── engine.py    # 文档加载、分块、向量化、混合检索
├── tools/
│   ├── registry.py  # 工具注册中心
│   └── builtin/     # 订单查询 / CRM / FAQ 三个内置工具
├── workflow/
│   └── graph.py     # LangGraph 状态图，整个系统的编排逻辑
├── memory/          # 对话记忆管理
├── models/          # Pydantic 请求响应模型
├── api/             # FastAPI 路由，SSE 流式 + 同步接口
└── config.py        # 全部配置，环境变量注入
```

## 技术选型

- **LangGraph** 而不是 AutoGen/CrewAI — 喜欢它显式的状态图，调试起来比黑盒编排清晰得多
- **ChromaDB** — 轻量，Python 原生，单机跑够用了
- **Qwen (DashScope)** — 中文效果不错，API 兼容 OpenAI SDK，换模型不用改代码
- **FastAPI** — 异步原生支持好，SSE 流式不用额外折腾

## 参考

写这个项目的过程中主要看了这些：

- LangGraph 官方文档的 Agent Supervisor 示例
- DataWhale 的 hello-agents 教程（面试问题总结那章特别有用）
- 知乎上几篇关于 RRF 融合排序的文章
- ChromaDB 的 HNSW 参数调优讨论
