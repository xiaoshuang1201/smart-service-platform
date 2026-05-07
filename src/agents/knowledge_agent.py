# KnowledgeAgent — 基于 RAG 的知识库问答

from __future__ import annotations
from typing import Any

from src.agents.base import BaseAgent
from src.rag.engine import hybrid_retriever

RAG_SYSTEM_PROMPT = """你是 SmartService 智能客服。基于提供的知识库内容回答用户问题。

## 规则
1. 仅根据「参考资料」回答，不要编造
2. 如果参考资料中找不到答案，诚实说"我暂时无法回答这个问题，需要我帮您转接人工客服吗？"
3. 回答时引用具体的文档来源
4. 回答简洁、直接，控制在 300 字以内
5. 如果用户提供了订单号或手机号，建议用户使用订单查询功能

## 参考资料
{context}
"""

class KnowledgeAgent(BaseAgent):
    """
    知识库问答 Agent
    职责：RAG 检索 → 结合检索结果用 LLM 生成回答
    """

    def __init__(self):
        super().__init__("KnowledgeAgent")

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_message = state.get("user_message", "")
        intent = state.get("intent")

        # 1. 检索相关文档
        retrieved = await hybrid_retriever.retrieve(user_message, top_k=5)

        # 2. 构建上下文
        if retrieved:
            context_parts = []
            for i, r in enumerate(retrieved):
                src = r.get("metadata", {}).get("filename", "未知来源")
                context_parts.append(f"[{i+1}] 来源: {src}\n{r['content']}")
            context = "\n\n".join(context_parts)
        else:
            context = "（无相关参考资料）"

        # 3. LLM 生成回答
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT.format(context=context)},
            {"role": "user", "content": user_message},
        ]

        answer, usage = await self._call_llm(messages)

        # 4. 计算整体置信度（取检索结果最高分，如果没有则 0.3）
        top_score = retrieved[0]["score"] if retrieved else 0.3

        return {
            "agent_response": answer,
            "retrieved_chunks": retrieved,
            "confidence": top_score,
            "usage_knowledge": usage,
        }
