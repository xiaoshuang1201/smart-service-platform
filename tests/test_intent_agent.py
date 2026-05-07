# 意图识别 Agent 单元测试

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.intent_agent import IntentAgent, _fallback_intent


class TestFallbackIntent:
    """规则兜底逻辑测试（不依赖 LLM）"""

    def test_order_query_detection(self):
        result = _fallback_intent("我的订单 20260507001 什么时候发货？")
        assert result["intent"] == "order_query"
        assert result["entities"].get("order_id") == "20260507001"

    def test_complaint_detection(self):
        result = _fallback_intent("我要投诉你们的产品质量太差了")
        assert result["intent"] == "complaint"
        assert result["sentiment"] == "angry"

    def test_human_handoff_detection(self):
        result = _fallback_intent("转人工客服")
        assert result["intent"] == "human_handoff"

    def test_knowledge_qa_default(self):
        result = _fallback_intent("你们退换货政策是什么？")
        assert result["intent"] == "knowledge_qa"
        assert result["sentiment"] == "neutral"

    def test_phone_extraction(self):
        result = _fallback_intent("手机号13800001111帮我查一下")
        assert result["entities"].get("phone") == "13800001111"


class TestIntentAgent:
    """完整 IntentAgent 测试（Mock LLM 调用）"""

    @pytest.mark.asyncio
    async def test_intent_classification(self):
        agent = IntentAgent()

        mock_response = type("MockResponse", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {
                        "content": '{"intent":"knowledge_qa","entities":{},"sentiment":"neutral","confidence":0.92}'
                    })()
                })()
            ],
            "usage": type("Usage", (), {
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "total_tokens": 150,
            })()
        })()

        with patch.object(agent, '_call_llm', AsyncMock(return_value=(
            '{"intent":"knowledge_qa","entities":{},"sentiment":"neutral","confidence":0.92}',
            {"total_tokens": 150, "prompt_tokens": 120, "completion_tokens": 30}
        ))):
            result = await agent.execute({
                "user_message": "你们退换货政策是什么？",
                "conversation_history": [],
            })

            assert result["intent"].intent == "knowledge_qa"
            assert result["intent"].confidence == 0.92
            assert "usage_intent" in result

    @pytest.mark.asyncio
    async def test_angry_complaint_forces_handoff(self):
        agent = IntentAgent()

        response = '{"intent":"complaint","entities":{},"sentiment":"angry","confidence":0.88}'
        with patch.object(agent, '_call_llm', AsyncMock(return_value=(
            response, {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        ))):
            result = await agent.execute({
                "user_message": "垃圾产品，我要投诉你们！",
                "conversation_history": [],
            })

            # 愤怒投诉 → 强制转人工
            assert result["intent"].intent == "human_handoff"
