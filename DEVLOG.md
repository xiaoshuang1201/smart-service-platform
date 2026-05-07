# 开发日志

随手记的，主要怕自己忘了当时为什么做某些决策。

## Day 1-2 (5.4 - 5.5) — 项目骨架 + RAG

- 搭项目结构花了半天，纠结了一下要不要用 DDD 分层，后来觉得太过了，就按功能拆了 agents/rag/tools 三个目录
- 文档分块试了固定长度（chunk_size=500），效果很差，经常把一段完整说明从中间切开。换成 RecursiveCharacterTextSplitter 按 `\n##` → `\n` → `。` 优先级切，好多了
- **踩坑**：ChromaDB 第一次跑的时候 collection 创建了但查不到数据，debug 半天发现是 persist_directory 路径包含中文，换英文路径解决

## Day 3-4 (5.5 - 5.6) — Intent + Action Agent

- IntentAgent 最开始只用了 LLM 做分类，后来发现有些边界 case 不稳定（比如"我要投诉"被分到了 knowledge_qa），加了一层规则兜底
- 工具注册中心一开始用 dict 写的，后面改成 Protocol 接口，方便加新工具的时候不会漏方法
- FAQ 匹配最初也想走 LLM，但算了一下 token 成本 —— 一个 FAQ 问题几毛钱太贵了，而且回答内容本来就固定，改成关键词匹配 + 规则阈值，P99 < 200ms
- **踩坑**：ActionAgent 的 JSON 输出偶尔被 ```json 包裹，解析不了一直报错。加了个 if "```" in content 的处理

## Day 5-6 (5.6 - 5.7) — LangGraph 编排

- 看了一下午 LangGraph 文档，终于把 StateGraph 和条件路由搞清楚了。最花时间的是想清楚什么时候走 RAG、什么时候走工具调用、什么时候转人工
- 置信度阈值设的 0.7，老实说是拍脑袋的。后面要跑一批真实客服对话数据来确定更好的阈值
- 记忆模块的摘要压缩太简陋了——现在就是把历史消息拼一起截断，正经做法应该用 LLM 做总结。先记 TODO 后面改

## Day 7-8 (5.7) — 测试 + Docker

- 测试覆盖率搞到了 80% 多，IntentAgent 和 Tool 的都比较好写，但 LangGraph 的集成测试不太好 mock，只写了 API 层的测试
- Docker Compose 一开始用 `depends_on` 发现 postgres 还没 ready 的时候 API 就启动报错了，加了个 healthcheck 解决

## 还没做完的

- [ ] 把 summary 改成 LLM 摘要（现在就一个截断，太糙了）
- [ ] 加 LangSmith 做 Agent 调用链可视化
- [ ] FAQ 库改成 Redis，现在硬编码在代码里
- [ ] 知识库支持增量更新，现在每次都是全量重建索引
- [ ] 对话记忆接 Redis 持久化，现在重启就没了
- [ ] 前端用 React 重写一版
