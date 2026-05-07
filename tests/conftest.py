# pytest 配置和共享 fixtures

import pytest
import os

# 测试模式：使用 mock，不调用真实 LLM API
os.environ["DEBUG"] = "true"


@pytest.fixture
def sample_user_message():
    return "我的订单 20260507001 什么时候到货？"


@pytest.fixture
def sample_knowledge_question():
    return "如何申请退货退款？"


@pytest.fixture
def sample_complaint_message():
    return "你们的产品太差了，我要投诉！"


@pytest.fixture
def mock_intent_result():
    from src.models.schemas import IntentResult
    return IntentResult(
        intent="order_query",
        entities={"order_id": "20260507001"},
        sentiment="neutral",
        confidence=0.95,
    )
