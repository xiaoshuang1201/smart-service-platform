# LangGraph 编排器 — 多 Agent 协同的状态图
#
# 花了一下午才理清这个状态图，核心问题是:
#   1. 什么时候走 RAG、什么时候调工具、什么时候转人工？
#   2. 置信度阈值设多少？(先拍脑袋设 0.7，后面有标注数据再调)
#   3. 记忆怎么在节点间传递？LangGraph 的 State 机制挺好用，但要注意 key 不能冲突
#
# 参考了 LangGraph 官方的 supervisor agent 例子，改成了适合自己的场景

from __future__ import annotations
import time
import uuid
import logging
from typing import Any, TypedDict, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.config import config
from src.agents.intent_agent import IntentAgent
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.action_agent import ActionAgent
from src.memory.conversation_memory import memory_manager
from src.models.schemas import IntentResult


# ─── 状态定义 ────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """LangGraph 全局状态 — 在各个 Agent 节点间流转"""
    trace_id: str
    session_id: str
    user_message: str
    user_id: str | None

    # 意图识别结果
    intent: IntentResult | None

    # 各 Agent 产出
    agent_response: str
    confidence: float

    # 工具调用记录
    tool_calls: list[dict]

    # RAG 检索结果
    retrieved_chunks: list[dict]

    # Token 用量追踪
    usage_intent: dict
    usage_knowledge: dict
    usage_action: dict

    # 路由决策
    route_decision: str
    should_escalate: bool

    # 耗时
    start_time: float


# ─── Agent 实例 ──────────────────────────────────────

intent_agent = IntentAgent()
knowledge_agent = KnowledgeAgent()
action_agent = ActionAgent()

# ─── 节点函数 ────────────────────────────────────────

async def node_intent_classify(state: AgentState) -> dict:
    """节点1: 意图识别"""
    result = await intent_agent.execute(state)
    return result

async def node_knowledge_rag(state: AgentState) -> dict:
    """节点2: 知识库RAG问答"""
    result = await knowledge_agent.execute(state)
    return result

async def node_action_tools(state: AgentState) -> dict:
    """节点3: 工具调用"""
    result = await action_agent.execute(state)
    return result

async def node_human_handoff(state: AgentState) -> dict:
    """节点4: 转接人工"""
    return {
        "agent_response": "正在为您转接人工客服，请稍候...（预计等待时间 < 1 分钟）\n\n在等待期间，您可以先描述一下您遇到的问题，客服接入后会第一时间看到。",
        "confidence": 1.0,
        "should_escalate": True,
    }

async def node_check_confidence(state: AgentState) -> dict:
    """节点5: 置信度检查"""
    confidence = state.get("confidence", 0.5)
    should_escalate = confidence < config.agent.confidence_threshold
    return {"should_escalate": should_escalate}


# ─── 路由函数 ────────────────────────────────────────

def route_by_intent(state: AgentState) -> Literal["knowledge_rag", "action_tools", "human_handoff"]:
    """根据意图路由到对应节点"""
    intent = state.get("intent")
    if not intent:
        return "knowledge_rag"

    intent_name = intent.intent

    if intent_name == "human_handoff":
        return "human_handoff"
    elif intent_name in ("order_query", "crm_lookup"):
        return "action_tools"
    elif intent_name == "complaint":
        return "human_handoff"
    else:
        return "knowledge_rag"

def route_by_confidence(state: AgentState) -> Literal["output", "human_handoff"]:
    """置信度不足时转人工"""
    if state.get("should_escalate", False):
        return "human_handoff"
    return "output"


# ─── 构建状态图 ──────────────────────────────────────

def build_orchestrator() -> StateGraph:
    """构建 LangGraph 多Agent协同编排图"""
    workflow = StateGraph(AgentState)

    # 注册节点
    workflow.add_node("intent_classify", node_intent_classify)
    workflow.add_node("knowledge_rag", node_knowledge_rag)
    workflow.add_node("action_tools", node_action_tools)
    workflow.add_node("human_handoff", node_human_handoff)
    workflow.add_node("check_confidence", node_check_confidence)

    # 设置入口和边
    workflow.set_entry_point("intent_classify")

    # 意图 → 路由
    workflow.add_conditional_edges(
        "intent_classify",
        route_by_intent,
        {"knowledge_rag": "knowledge_rag", "action_tools": "action_tools", "human_handoff": "human_handoff"},
    )

    # RAG/工具 结束后 → 置信度检查
    workflow.add_edge("knowledge_rag", "check_confidence")
    workflow.add_edge("action_tools", "check_confidence")

    # 置信度检查 → 正常输出 或 转人工
    workflow.add_conditional_edges(
        "check_confidence",
        route_by_confidence,
        {"output": END, "human_handoff": "human_handoff"},
    )

    # 人工转接后 → 结束
    workflow.add_edge("human_handoff", END)

    # 编译（使用内存检查点，生产环境改 PostgresSaver）
    memory_saver = MemorySaver()
    compiled = workflow.compile(checkpointer=memory_saver)
    return compiled


# 全局编排器实例
orchestrator = build_orchestrator()


# ─── 对外调用入口 ────────────────────────────────────

logger = logging.getLogger(__name__)


async def run_orchestrator(
    user_message: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    """执行一次完整的 Agent 协同流程"""
    session_id = session_id or uuid.uuid4().hex[:16]
    trace_id = uuid.uuid4().hex[:12]

    # 初始化状态
    initial_state: AgentState = {
        "trace_id": trace_id,
        "session_id": session_id,
        "user_message": user_message,
        "user_id": user_id,
        "intent": None,
        "agent_response": "",
        "confidence": 0.0,
        "tool_calls": [],
        "retrieved_chunks": [],
        "usage_intent": {},
        "usage_knowledge": {},
        "usage_action": {},
        "route_decision": "",
        "should_escalate": False,
        "start_time": time.time(),
    }

    # 执行 LangGraph
    config_dict = {"configurable": {"thread_id": session_id}}
    try:
        final_state = await orchestrator.ainvoke(initial_state, config_dict)
    except Exception as e:
        logger.error(f"[Orchestrator] Pipeline failed for trace {trace_id}: {e}")
        total_latency = (time.time() - initial_state["start_time"]) * 1000
        return {
            "trace_id": trace_id,
            "session_id": session_id,
            "response": "抱歉，系统暂时遇到了一些问题，正在为您转接人工客服...",
            "intent": None,
            "confidence": 0.0,
            "tool_calls": [],
            "should_escalate": True,
            "total_latency_ms": int(total_latency),
            "total_tokens": 0,
        }

    # 保存到对话记忆
    memory_manager.add_message(session_id, "user", user_message)
    memory_manager.add_message(session_id, "assistant", final_state.get("agent_response", ""))

    # 汇总结果
    total_latency = (time.time() - initial_state["start_time"]) * 1000
    total_tokens = sum(
        final_state.get(k, {}).get("total_tokens", 0)
        for k in ("usage_intent", "usage_knowledge", "usage_action")
    )

    return {
        "trace_id": trace_id,
        "session_id": session_id,
        "response": final_state.get("agent_response", "抱歉，系统暂时无法处理您的请求。"),
        "intent": final_state.get("intent"),
        "confidence": final_state.get("confidence", 0.0),
        "tool_calls": final_state.get("tool_calls", []),
        "should_escalate": final_state.get("should_escalate", False),
        "total_latency_ms": int(total_latency),
        "total_tokens": total_tokens,
    }
