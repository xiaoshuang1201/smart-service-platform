# Pydantic 数据模型 — API 请求/响应定义

from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

# ─── 对话相关 ──────────────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None  # 新对话时为 None
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: Optional[str] = None

class ChatEvent(BaseModel):
    """SSE 流式响应中的单个事件"""
    event: str  # token | tool_call_start | tool_call_end | error | done
    data: dict[str, Any]
    trace_id: str = Field(default_factory=lambda: uuid4().hex[:12])

class ConversationInfo(BaseModel):
    id: UUID
    user_id: Optional[str]
    status: str
    intent: Optional[str]
    sentiment: Optional[str]
    created_at: datetime
    message_count: int = 0

class MessageInfo(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

# ─── 知识库相关 ──────────────────────────────────────

class DocumentInfo(BaseModel):
    id: UUID
    filename: str
    file_type: Optional[str]
    chunk_count: int
    status: str  # pending | indexing | ready | failed
    created_at: datetime

class KnowledgeHealth(BaseModel):
    total_documents: int
    total_chunks: int
    collection_name: str
    status: str  # healthy | degraded | down

# ─── Agent 相关 ──────────────────────────────────────

class IntentResult(BaseModel):
    intent: str  # knowledge_qa | order_query | crm_lookup | complaint | human_handoff
    entities: dict[str, Any] = Field(default_factory=dict)
    sentiment: str = "neutral"  # neutral | anxious | angry
    confidence: float = 0.0

class ToolCallRecord(BaseModel):
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    status: str = "pending"  # pending | running | success | failed | timeout
    latency_ms: int = 0

class AgentTrace(BaseModel):
    """单次 Agent 调用的完整追踪"""
    trace_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    intent: Optional[IntentResult] = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    final_response: Optional[str] = None
    total_latency_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)

# ─── 管理后台 ────────────────────────────────────────

class DashboardStats(BaseModel):
    total_conversations: int
    active_conversations: int
    auto_resolved: int
    human_escalated: int
    avg_response_time_ms: int
    avg_confidence: float
    total_token_usage: int
    period: str = "today"  # today | week | month
