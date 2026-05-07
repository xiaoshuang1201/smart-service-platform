# ActionAgent — 工具调用(订单查询/CRM查询/FAQ匹配)

from __future__ import annotations
import json
from typing import Any

from src.agents.base import BaseAgent
from src.tools.registry import tool_registry

TOOL_SYSTEM_PROMPT = """你是 SmartService 工具调度器。根据用户意图和实体，决定调用哪些工具。

## 可用工具
{tool_descriptions}

## 输出格式 (仅输出 JSON)
{{
    "tool_calls": [
        {{"tool_name": "order_query", "params": {{"order_id": "20260507001"}}}}
    ],
    "reasoning": "用户询问订单状态，需要调用 order_query"
}}

如果不需要调用任何工具，返回：
{{"tool_calls": [], "reasoning": "无需工具调用"}}
"""

class ActionAgent(BaseAgent):
    """
    工具调度 Agent
    职责：根据意图和实体 → 规划工具调用顺序 → 依次执行 → 聚合结果生成自然语言回复
    """

    def __init__(self):
        super().__init__("ActionAgent")
        self._registry = tool_registry

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_message = state.get("user_message", "")
        intent = state.get("intent")
        entities = intent.entities if intent else {}

        # 1. LLM 规划需要调用的工具
        tool_plan = await self._plan_tools(user_message, intent, entities)

        # 2. 依次执行工具调用
        tool_results = []
        for call in tool_plan.get("tool_calls", [])[:3]:  # 最多 3 个工具
            result = await self._execute_tool(call["tool_name"], call.get("params", {}))
            tool_results.append(result)

        # 3. 如果没有工具调用，走 FAQ 精确匹配兜底
        if not tool_results:
            faq_result = await self._execute_tool("faq_match", {"query": user_message})
            if faq_result["status"] == "success" and faq_result["result"]:
                return {
                    "agent_response": faq_result["result"],
                    "tool_calls": [faq_result],
                    "confidence": 0.95,
                }

        # 4. 聚合工具结果生成自然语言回复
        if tool_results:
            response, usage = await self._summarize_results(user_message, tool_results)
        else:
            response = "我暂时无法处理这个请求，需要我帮您转接人工客服吗？"
            usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        success_count = sum(1 for r in tool_results if r["status"] == "success")
        confidence = 0.85 if success_count == len(tool_results) else 0.5

        return {
            "agent_response": response,
            "tool_calls": tool_results,
            "confidence": confidence,
            "usage_action": usage,
        }

    async def _plan_tools(self, user_message: str, intent: Any, entities: dict) -> dict:
        """让 LLM 规划需要调用哪些工具"""
        tool_descs = self._registry.describe_all()
        tool_descs_text = "\n".join(
            f"- {t['name']}: {t['description']} (参数: {json.dumps(t['params'], ensure_ascii=False)})"
            for t in tool_descs
        )

        messages = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT.format(tool_descriptions=tool_descs_text)},
            {"role": "user", "content": f"意图: {intent.intent if intent else 'unknown'}\n"
                                        f"实体: {json.dumps(entities, ensure_ascii=False)}\n"
                                        f"用户消息: {user_message}"},
        ]

        content, _ = await self._call_llm(messages, temperature=0.05)
        try:
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except json.JSONDecodeError:
            # 解析失败 → 规则兜底
            return _rule_based_tool_plan(intent, entities)

    async def _execute_tool(self, tool_name: str, params: dict) -> dict:
        """执行单个工具调用"""
        tool = self._registry.get(tool_name)
        if not tool:
            return {"tool_name": tool_name, "params": params, "result": None,
                    "status": "failed", "error": f"Tool '{tool_name}' not found"}

        try:
            result = await tool.execute(**params)
            return {"tool_name": tool_name, "params": params, "result": result,
                    "status": "success"}
        except Exception as e:
            return {"tool_name": tool_name, "params": params, "result": None,
                    "status": "failed", "error": str(e)}

    async def _summarize_results(self, user_message: str, tool_results: list[dict]) -> tuple[str, dict]:
        """将工具结果聚合为自然语言回复"""
        results_text = json.dumps(
            [{"tool": r["tool_name"], "result": r.get("result")} for r in tool_results],
            ensure_ascii=False, indent=2
        )

        messages = [
            {"role": "system", "content": "你是客服助手。根据工具返回的数据，用自然语言回答用户。保持简洁、友好。"},
            {"role": "user", "content": f"用户问题: {user_message}\n\n工具返回数据:\n{results_text}"},
        ]
        return await self._call_llm(messages)


def _rule_based_tool_plan(intent: Any, entities: dict) -> dict:
    """规则兜底 — LLM工具规划失败时直接按意图匹配"""
    intent_name = intent.intent if intent else "knowledge_qa"
    tool_map = {
        "order_query": ["order_query"],
        "crm_lookup": ["crm_lookup"],
        "human_handoff": [],
        "complaint": [],
        "knowledge_qa": ["faq_match"],
    }
    tool_names = tool_map.get(intent_name, [])
    calls = []
    for name in tool_names:
        params = {}
        if name == "order_query" and "order_id" in entities:
            params["order_id"] = entities["order_id"]
        elif name == "crm_lookup" and "phone" in entities:
            params["phone"] = entities["phone"]
        calls.append({"tool_name": name, "params": params})

    return {"tool_calls": calls, "reasoning": f"Rule-based routing for intent: {intent_name}"}
