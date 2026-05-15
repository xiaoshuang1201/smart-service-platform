# 工具系统单元测试

import pytest
from src.tools.builtin.order_query import OrderQueryTool
from src.tools.builtin.crm_lookup import CRMLookupTool
from src.tools.builtin.faq_match import FAQMatchTool
from src.tools.registry import ToolRegistry


class TestOrderQuery:
    @pytest.mark.asyncio
    async def test_existing_order(self):
        tool = OrderQueryTool()
        result = await tool.execute(order_id="20260507001")
        assert result["found"] is True
        assert result["status"] == "运输中"
        assert result["carrier"] == "顺丰速运"
        assert result["total"] == 299.0
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_nonexistent_order(self):
        tool = OrderQueryTool()
        result = await tool.execute(order_id="99999999999")
        assert result["found"] is False
        assert "未找到" in result["message"]


class TestCRMLookup:
    @pytest.mark.asyncio
    async def test_existing_user(self):
        tool = CRMLookupTool()
        result = await tool.execute(phone="13800001111")
        assert result["found"] is True
        assert result["level"] == "金牌会员"
        assert "****" in result["phone"]
        assert len(result["phone"]) == 11  # 3 + 4 + 4 = 11

    @pytest.mark.asyncio
    async def test_nonexistent_user(self):
        tool = CRMLookupTool()
        result = await tool.execute(phone="19999999999")
        assert result["found"] is False


class TestFAQMatch:
    @pytest.mark.asyncio
    async def test_exact_match(self):
        tool = FAQMatchTool()
        result = await tool.execute(query="我想退货退款怎么操作")
        assert result is not None
        assert "申请售后" in result

    @pytest.mark.asyncio
    async def test_partial_match(self):
        tool = FAQMatchTool()
        result = await tool.execute(query="我的东西什么时候发货")
        assert result is not None
        assert "48小时" in result

    @pytest.mark.asyncio
    async def test_no_match(self):
        tool = FAQMatchTool()
        result = await tool.execute(query="今天天气怎么样")
        assert result is None


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = OrderQueryTool()
        registry.register(tool)
        assert registry.get("order_query") is tool
        assert "order_query" in registry.list_all()

    def test_duplicate_register_raises(self):
        registry = ToolRegistry()
        registry.register(OrderQueryTool())
        with pytest.raises(ValueError):
            registry.register(OrderQueryTool())

    def test_describe_all(self):
        registry = ToolRegistry()
        registry.register(OrderQueryTool())
        desc = registry.describe_all()
        assert len(desc) == 1
        assert desc[0]["name"] == "order_query"
        assert "params" in desc[0]
