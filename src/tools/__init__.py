# 自动注册所有内置工具
from src.tools.registry import tool_registry
from src.tools.builtin.order_query import OrderQueryTool
from src.tools.builtin.crm_lookup import CRMLookupTool
from src.tools.builtin.faq_match import FAQMatchTool

def register_all_tools():
    tool_registry.register(OrderQueryTool())
    tool_registry.register(CRMLookupTool())
    tool_registry.register(FAQMatchTool())
