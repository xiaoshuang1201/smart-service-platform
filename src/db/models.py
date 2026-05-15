"SQLAlchemy ORM 模型 — 对话、消息、文档、工具调用、用户"

from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from src.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid():
    return uuid.uuid4()


class ConversationStatus(str, enum.Enum):
    active = "active"
    closed = "closed"
    escalated = "escalated"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class ToolCallStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    timeout = "timeout"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    phone_hashed = Column(String(64), nullable=True, index=True)
    email_hashed = Column(String(64), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    status = Column(SAEnum(ConversationStatus), default=ConversationStatus.active, index=True)
    intent = Column(String(50), nullable=True)
    sentiment = Column(String(20), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    trace = Column(JSON, nullable=True)
    token_count = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    conversation = relationship("Conversation", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=True)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.pending, index=True)
    minio_path = Column(String(1000), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    input_params = Column(JSON, default=dict)
    output_result = Column(JSON, nullable=True)
    status = Column(SAEnum(ToolCallStatus), default=ToolCallStatus.success, index=True)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    message = relationship("Message", back_populates="tool_calls")
