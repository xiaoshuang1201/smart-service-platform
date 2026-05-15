# 对话记忆管理 — 会话内上下文 + 超长对话自动压缩

from __future__ import annotations
import logging
from typing import Any, Callable
from collections import OrderedDict
import time

from src.config import config

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    基于滑动窗口 + 摘要压缩的对话记忆管理

    策略：
    - 保留最近 window_size 轮完整对话
    - 超出部分自动压缩为摘要（支持 LLM 摘要或规则摘要）
    """

    def __init__(self):
        # session_id -> { "messages": [...], "summary": str, "created_at": float, "last_access": float }
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._max_sessions = 1000
        self._summarizer: Callable | None = None

    def set_llm_summarizer(self, fn: Callable) -> None:
        """注入 LLM 摘要函数: async fn(messages: list[dict]) -> str"""
        self._summarizer = fn

    def get_or_create_session(self, session_id: str) -> dict:
        if session_id not in self._store:
            if len(self._store) >= self._max_sessions:
                oldest = next(iter(self._store))
                del self._store[oldest]
            self._store[session_id] = {
                "messages": [],
                "summary": "",
                "created_at": time.time(),
                "last_access": time.time(),
            }
        self._store[session_id]["last_access"] = time.time()
        return self._store[session_id]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self.get_or_create_session(session_id)
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })

        if len(session["messages"]) > config.memory.summary_threshold * 2:
            self._compress(session_id)

    def get_context(self, session_id: str, n: int | None = None) -> list[dict]:
        """获取用于 LLM 调用的上下文窗口"""
        session = self.get_or_create_session(session_id)
        if n is None:
            n = config.memory.window_size * 2

        recent = session["messages"][-n:]
        context = []
        if session["summary"]:
            context.append({"role": "system", "content": f"[对话历史摘要] {session['summary']}"})
        context.extend(recent)
        return context

    def _compress(self, session_id: str) -> None:
        """将旧对话压缩为摘要"""
        session = self._store.get(session_id)
        if not session:
            return
        messages = session["messages"]
        if len(messages) <= config.memory.summary_threshold * 2:
            return

        keep = config.memory.window_size * 2
        old = messages[:-keep]

        if self._summarizer:
            try:
                summary = self._run_llm_summary(old)
                if summary:
                    session["summary"] = summary
                    session["messages"] = messages[-keep:]
                    return
            except Exception as e:
                logger.warning(f"LLM summary failed, falling back to rule-based: {e}")

        # 规则兜底
        summary_parts = []
        for m in old[-10:]:
            if m["role"] == "user":
                summary_parts.append(f"用户问: {m['content'][:80]}")
        if summary_parts:
            session["summary"] = "；".join(summary_parts)
        session["messages"] = messages[-keep:]

    def _run_llm_summary(self, messages: list[dict]) -> str:
        """同步调用 LLM 摘要函数"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(
                    self._summarizer(messages), loop
                )
                return future.result(timeout=10)
            else:
                return asyncio.run(self._summarizer(messages))
        except Exception:
            raise

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """清理过期会话"""
        now = time.time()
        expired = [
            sid for sid, s in self._store.items()
            if now - s["last_access"] > config.memory.session_ttl
        ]
        for sid in expired:
            del self._store[sid]
        return len(expired)

# 全局单例
memory_manager = ConversationMemory()
