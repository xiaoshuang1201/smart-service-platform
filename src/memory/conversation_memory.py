# 对话记忆管理 — 会话内上下文 + 超长对话自动压缩
#
# 当前实现比较简陋:
#   - _compress() 只是拼历史消息截断，正经做法应该用 LLM 做摘要
#   - 存内存里，服务重启全丢，生产环境得接 Redis
#   - window_size 和 summary_threshold 这两个参数拍脑袋设的
# TODO: 摘要压缩换成 LLM 来做，内存存储换成 Redis

from __future__ import annotations
from typing import Any
from collections import OrderedDict
import time

from src.config import config

class ConversationMemory:
    """
    基于滑动窗口 + 摘要压缩的对话记忆管理

    策略：
    - 保留最近 window_size 轮完整对话
    - 超出部分自动压缩为摘要
    - 支持 Redis 持久化（生产环境）
    """

    def __init__(self):
        # session_id -> { "messages": [...], "summary": str, "created_at": float, "last_access": float }
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._max_sessions = 1000

    def get_or_create_session(self, session_id: str) -> dict:
        if session_id not in self._store:
            if len(self._store) >= self._max_sessions:
                # LRU 淘汰
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

        # 超过阈值时自动压缩
        if len(session["messages"]) > config.memory.summary_threshold * 2:
            self._compress(session_id)

    def get_context(self, session_id: str, n: int | None = None) -> list[dict]:
        """获取用于 LLM 调用的上下文窗口"""
        session = self.get_or_create_session(session_id)
        if n is None:
            n = config.memory.window_size * 2  # 2 条消息 = 1 轮对话

        recent = session["messages"][-n:]
        context = []
        if session["summary"]:
            context.append({"role": "system", "content": f"[对话历史摘要] {session['summary']}"})
        context.extend(recent)
        return context

    def _compress(self, session_id: str) -> None:
        """将旧对话压缩为摘要（生产环境建议用 LLM 做摘要）"""
        session = self._store.get(session_id)
        if not session:
            return
        messages = session["messages"]
        if len(messages) <= config.memory.summary_threshold * 2:
            return

        # 保留最近 window_size 轮
        keep = config.memory.window_size * 2
        old = messages[:-keep]

        # 简单摘要：拼接最近的关键信息
        summary_parts = []
        for m in old:
            if m["role"] == "user":
                summary_parts.append(f"用户问: {m['content'][:80]}")
        session["summary"] = "；".join(summary_parts[-5:])  # 保留最近 5 条摘要
        session["messages"] = messages[-keep:]

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
