# TODO

## 近期

- [ ] FAQ 匹配库从代码里拆出来放 Redis，现在硬编码太蠢了
- [ ] 对话记忆接 Redis 持久化，不然重启全丢
- [ ] 长对话摘要压缩用 LLM 做，别截断了
- [ ] 写一个 confidence threshold 的自动调参脚本，跑一批标注数据

## 中期

- [ ] ChromaDB 换成 Milvus，数据量上来以后 Chroma 的检索延迟顶不住
- [ ] 加 LangSmith / LangFuse 做调用链追踪，现在 debug Agent 全靠 print
- [ ] 前端换成 React + 对话组件库，Streamlit 面试 demo 还行，真用不太行

## 远期

- [ ] MCP Server 把内置工具暴露出去，这样其他 Agent 平台也能调用
- [ ] 加一个 code-interpreter tool，让 Agent 能执行简单逻辑
- [ ] 知识库增量更新，每次全量建索引太慢了
- [ ] 多语言支持（先做英文）
