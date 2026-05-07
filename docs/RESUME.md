# SmartService — 简历项目描述（ATS优化版）

## 项目标题

> **SmartService — 基于 LangGraph 的企业级多智能体客服协同平台**
>
> GitHub: https://github.com/xiaoshuang1201/smart-service-platform

---

## 版本一：完整版（适合简历"项目经历"栏，主推）

```
SmartService — 企业级多智能体客服协同平台（LangGraph + RAG + Qwen）

基于 LangGraph 构建三Agent协同智能客服系统，实现意图识别→RAG问答/工具调用→置信度
检查→人工转接全链路自动化编排。系统日均可处理 5000+ 会话，自动解决率 60%+，单次
响应延迟 < 3秒。

· 多Agent协同架构：设计 IntentAgent（意图识别+实体提取）、KnowledgeAgent（RAG知识
  问答）、ActionAgent（工具动态调度）三Agent体系，通过 LangGraph StateGraph 实现5
  节点条件路由状态机，支持 Agent 自动协同与异常降级人工转接

· 混合检索 RAG 引擎：基于 ChromaDB 向量检索 + jieba-BM25 关键词检索 + RRF 融合排序
  构建混合检索引擎，配合 text-embedding-v3 (1024维) 实现语义级知识问答；文档自动分块
  (RecursiveCharacterTextSplitter)、Reranker重排序、引用溯源，检索召回率 92%+

· 工具调用（Function Calling）体系：实现订单查询、CRM客户查询、FAQ关键词匹配（零LLM、
  毫秒级响应）等工具的统一注册-发现-执行框架，LLM 动态规划工具调用序列并聚合结果
  为自然语言回复，工具调用成功率 94%+

· 对话记忆与流式响应：滑动窗口记忆管理（近10轮）+ 超长对话自动摘要压缩；FastAPI
  SSE 流式推送 Agent 思考过程（意图/工具调用/最终回复）；PII数据自动脱敏

· 工程化落地：Docker Compose 一键部署（6服务编排），pytest 单元测试+集成测试
  （覆盖率 > 80%），Token消耗追踪与成本分析，RESTful API + OpenAPI 自动文档
```

---

## 版本二：精炼版（适合简历空间紧张时）

```
SmartService — 基于 LangGraph 的多Agent客服协同平台（LangGraph + RAG + Qwen）

· 设计并实现三Agent协同架构（IntentAgent / KnowledgeAgent / ActionAgent），通过
  LangGraph StateGraph 编排 5 节点条件路由，实现全链路自动化，自动解决率 60%+

· 构建混合检索 RAG 引擎：ChromaDB 向量检索 + BM25 关键词检索 + RRF 融合排序，
  文档自动分块与 Reranker 重排序，检索召回率 92%

· 实现工具动态调度体系：LLM 自动规划工具调用序列，支持订单/CRM/FAQ 多工具协同，
  FAQ 匹配零 LLM 调用（P99 < 200ms），工具调用成功率 94%

· FastAPI SSE 流式推送 + 对话记忆滑动窗口 + Docker Compose 一键部署
  + pytest 单元/集成测试（覆盖率 > 80%）

GitHub: https://github.com/xiaoshuang1201/smart-service-platform
```

---

## 版本三：一句话版（适合"个人技能"或"自我介绍"区域）

> 独立完成基于 LangGraph + RAG 的企业级多Agent客服系统，三Agent协同（意图/知识/工具），混合检索引擎召回率92%，工具调用成功率94%，Docker一键部署，源码开源在 GitHub。

---

## 为什么这样写（设计思路）

### ATS/AI 筛选关键词覆盖清单

| 关键词类别 | 命中的词 | 出现位置 |
|-----------|---------|---------|
| Agent框架 | LangGraph, StateGraph, 多Agent, 协同 | 标题+正文 |
| RAG | RAG, ChromaDB, 向量检索, BM25, RRF, Embedding, 混合检索 | 正文 |
| 工具调用 | Function Calling, 工具调用, 工具注册, LLM动态规划 | 正文 |
| 模型 | Qwen, text-embedding-v3, LLM | 标题+正文 |
| 后端 | FastAPI, SSE, 流式, RESTful API, OpenAPI | 正文 |
| 工程 | Docker, Docker Compose, pytest, 覆盖率 | 正文 |
| 指标 | 92%, 94%, 60%+, 5000+, <3秒, <200ms | 全文 |

### HR 7秒扫描路径

```
第1秒 → 项目标题: "LangGraph" + "多Agent" + "企业级" ✓ 技术关键词命中
第2秒 → "三Agent协同" + "全链路自动化" ✓ 概括清晰
第3秒 → "召回率92%" + "成功率94%" ✓ 有量化数字
第4秒 → 看到 5 个 bullet point，每个都有技术+成果 ✓ 内容详实
第5秒 → GitHub 链接 ✓ 可以点进去看
第6-7秒 → 判定: 候选人有完整的项目落地能力
```

### 对标通过大厂面试的简历特征

| 成功要素 | 本简历如何体现 |
|---------|--------------|
| **不写"熟悉XXX"** | 每句话都是"做了什么+技术实现+量化结果" |
| **技术决策可见** | 明确写"RRF融合排序""RecursiveCharacterTextSplitter"说明你懂原理 |
| **系统思维** | "三Agent协同""条件路由状态机"体现架构能力 |
| **工程意识** | Docker/pytest/覆盖率/Token成本，大厂看重 |
| **业务价值** | "自动解决率60%""日处理5000+"，不只是玩具 |

---

## GitHub 链接的使用策略

1. **README 就是你的技术面试开场白**：面试官点开链接，README 里的架构图和快速开始指南会直接展示你的工程素养

2. **在简历中放短链接**：如果觉得 `github.com/[用户名]/smart-service-platform` 太长，用 `git.io` 或 `bit.ly` 生成短链接

3. **面试时主动引导**：当面试官问"说说你的项目"，直接打开 GitHub 仓库，对着代码讲

4. **Star 和 Fork**：让朋友帮忙 Star，项目有 10+ Star 会让面试官觉得你的项目有价值
