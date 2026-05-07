# IntentAgent — 意图识别、实体提取、情绪分析

from __future__ import annotations
import json
from typing import Any

from src.agents.base import BaseAgent
from src.models.schemas import IntentResult

INTENT_SYSTEM_PROMPT = """你是一个客服意图识别专家。分析用户消息，输出 JSON。

## 意图类别
- knowledge_qa: 咨询产品使用/退换货政策/活动规则等
- order_query: 查询订单状态/物流/修改订单
- crm_lookup: 需要查询用户账户/积分/会员等级
- complaint: 投诉产品或服务
- human_handoff: 明确要求转人工客服

## 实体类型
- order_id: 订单号 (如 20260507001)
- phone: 手机号 (如 13812345678)
- product_name: 产品名
- amount: 金额

## 情绪
- neutral: 正常
- anxious: 焦急
- angry: 愤怒/不满

## 输出格式 (仅输出 JSON)
{"intent": "knowledge_qa", "entities": {}, "sentiment": "neutral", "confidence": 0.95}
"""

class IntentAgent(BaseAgent):
    """
    意图识别 Agent
    职责：接收用户消息 → 分类意图 + 提取实体 + 检测情绪
    不产生回复，仅输出结构化分析结果
    """

    def __init__(self):
        super().__init__("IntentAgent")

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_message = state.get("user_message", "")
        history = state.get("conversation_history", [])

        # 有对话历史时，提供上下文辅助意图消歧
        context = ""
        if history:
            recent = history[-3:]  # 最近 3 轮
            context = "## 对话历史\n" + "\n".join(
                f"{'用户' if m['role'] == 'user' else '客服'}: {m['content'][:100]}"
                for m in recent
            )

        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n## 当前消息\n{user_message}"},
        ]

        content, usage = await self._call_llm(messages, temperature=0.05)

        # 解析 JSON 输出
        try:
            # 处理 LLM 可能返回的 markdown 代码块包裹
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content.strip())
        except json.JSONDecodeError:
            # 解析失败时的兜底策略 — 基于关键词的规则匹配
            result = _fallback_intent(user_message)

        intent_result = IntentResult(
            intent=result.get("intent", "knowledge_qa"),
            entities=result.get("entities", {}),
            sentiment=result.get("sentiment", "neutral"),
            confidence=result.get("confidence", 0.5),
        )

        # 强制转人工的场景
        if intent_result.sentiment == "angry" and intent_result.intent == "complaint":
            intent_result.intent = "human_handoff"

        return {
            "intent": intent_result,
            "usage_intent": usage,
        }


def _fallback_intent(user_message: str) -> dict:
    """规则兜底 — LLM 解析失败时的关键词匹配"""
    msg = user_message.lower()
    order_keywords = ["订单", "物流", "快递", "发货", "到货", "配送", "运单"]
    complaint_keywords = ["投诉", "差评", "垃圾", "太差", "骗", "举报"]
    human_keywords = ["人工", "转人工", "客服电话", "投诉电话"]

    if any(w in msg for w in human_keywords):
        return {"intent": "human_handoff", "entities": {}, "sentiment": "angry", "confidence": 0.8}
    if any(w in msg for w in complaint_keywords):
        return {"intent": "complaint", "entities": {}, "sentiment": "angry", "confidence": 0.7}

    import re
    entities = {}
    order_match = re.search(r"(\d{10,})", user_message)
    if order_match:
        entities["order_id"] = order_match.group(1)
    phone_match = re.search(r"(1[3-9]\d{9})", user_message)
    if phone_match:
        entities["phone"] = phone_match.group(1)

    if order_match or any(w in msg for w in order_keywords):
        return {"intent": "order_query", "entities": entities, "sentiment": "neutral", "confidence": 0.7}

    return {"intent": "knowledge_qa", "entities": entities, "sentiment": "neutral", "confidence": 0.6}
