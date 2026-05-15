"KnowledgeAgent 单元测试 — RAG 检索和回答生成"

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.knowledge_agent import KnowledgeAgent
from src.models.schemas import IntentResult


class TestKnowledgeAgent:
    @pytest.fixture
    def agent(self):
        return KnowledgeAgent()

    @pytest.fixture
    def sample_state(self):
        return {
            "user_message": "如何申请退货退款？",
            "intent": IntentResult(
                intent="knowledge_qa",
                entities={},
                sentiment="neutral",
                confidence=0.9,
            ),
        }

    @pytest.fixture
    def mock_retrieved_chunks(self):
        return [
            {
                "id": "chunk_001",
                "content": "退货流程：在订单详情页点击申请售后，选择退货退款。审核通过后3天内寄回商品，退款1-3个工作日到账。",
                "metadata": {"filename": "退货政策.md"},
                "score": 0.92,
            },
            {
                "id": "chunk_002",
                "content": "换货流程：在订单详情页点击申请售后→换货，审核通过后先寄新商品。",
                "metadata": {"filename": "退换货指南.md"},
                "score": 0.78,
            },
        ]

    @pytest.mark.asyncio
    async def test_execute_with_retrieved_chunks(
        self, agent, sample_state, mock_retrieved_chunks
    ):
        with patch(
            "src.agents.knowledge_agent.hybrid_retriever.retrieve",
            AsyncMock(return_value=mock_retrieved_chunks),
        ), patch.object(
            agent, "_call_llm",
            AsyncMock(return_value=("您可以在订单详情页申请退货退款。", {"total_tokens": 150})),
        ):
            result = await agent.execute(sample_state)
            assert "agent_response" in result
            assert "您可以在订单详情页" in result["agent_response"]
            assert result["confidence"] == 0.92
            assert len(result["retrieved_chunks"]) == 2
            assert result["usage_knowledge"]["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_execute_with_no_retrieved_chunks(self, agent, sample_state):
        with patch(
            "src.agents.knowledge_agent.hybrid_retriever.retrieve",
            AsyncMock(return_value=[]),
        ), patch.object(
            agent, "_call_llm",
            AsyncMock(return_value=(
                "我暂时无法回答这个问题，需要我帮您转接人工客服吗？",
                {"total_tokens": 80},
            )),
        ):
            result = await agent.execute(sample_state)
            assert result["confidence"] == 0.3
            assert len(result["retrieved_chunks"]) == 0

    @pytest.mark.asyncio
    async def test_context_includes_source_info(
        self, agent, sample_state, mock_retrieved_chunks
    ):
        captured_messages = []

        async def capture_call_llm(messages, **kwargs):
            captured_messages.extend(messages)
            return ("测试回答", {"total_tokens": 50})

        with patch(
            "src.agents.knowledge_agent.hybrid_retriever.retrieve",
            AsyncMock(return_value=mock_retrieved_chunks),
        ), patch.object(agent, "_call_llm", capture_call_llm):
            await agent.execute(sample_state)

            system_msg = captured_messages[0]["content"]
            assert "退货政策.md" in system_msg
            assert "退换货指南.md" in system_msg

    @pytest.mark.asyncio
    async def test_user_message_passed_to_llm(self, agent, sample_state, mock_retrieved_chunks):
        captured_messages = []

        async def capture_call_llm(messages, **kwargs):
            captured_messages.extend(messages)
            return ("回答", {"total_tokens": 30})

        with patch(
            "src.agents.knowledge_agent.hybrid_retriever.retrieve",
            AsyncMock(return_value=mock_retrieved_chunks),
        ), patch.object(agent, "_call_llm", capture_call_llm):
            await agent.execute(sample_state)

            user_msg = captured_messages[1]["content"]
            assert user_msg == "如何申请退货退款？"


class TestKnowledgeAgentWithoutIntent:
    @pytest.fixture
    def agent(self):
        return KnowledgeAgent()

    @pytest.mark.asyncio
    async def test_execute_without_intent_object(self, agent):
        state = {
            "user_message": "订单什么时候发货？",
            "intent": None,
        }
        with patch(
            "src.agents.knowledge_agent.hybrid_retriever.retrieve",
            AsyncMock(return_value=[]),
        ), patch.object(
            agent, "_call_llm",
            AsyncMock(return_value=("一般48小时内发货。", {"total_tokens": 60})),
        ):
            result = await agent.execute(state)
            assert result["agent_response"] == "一般48小时内发货。"
