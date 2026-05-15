"ConversationMemory 单元测试 — 滑动窗口、摘要压缩、LRU 淘汰"

import pytest
from unittest.mock import AsyncMock

from src.memory.conversation_memory import ConversationMemory, memory_manager
from src.config import config


class TestConversationMemory:
    @pytest.fixture
    def mem(self):
        m = ConversationMemory()
        yield m

    def test_add_message_and_get_context(self, mem):
        mem.add_message("s1", "user", "你好")
        mem.add_message("s1", "assistant", "您好，有什么可以帮您？")

        ctx = mem.get_context("s1")
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "assistant"

    def test_summary_when_threshold_exceeded(self, mem):
        session_id = "s2"
        for i in range(config.memory.summary_threshold * 2 + 2):
            mem.add_message(session_id, "user", f"问题 {i}")
            mem.add_message(session_id, "assistant", f"回答 {i}")

        session = mem._store["s2"]
        assert len(session["messages"]) <= config.memory.window_size * 2
        assert session["summary"] != ""

    def test_context_includes_summary(self, mem):
        session_id = "s3"
        for i in range(config.memory.summary_threshold * 2 + 2):
            mem.add_message(session_id, "user" if i % 2 == 0 else "assistant", f"消息 {i}")

        ctx = mem.get_context(session_id)
        has_summary = any(
            m["role"] == "system" and "对话历史摘要" in m["content"]
            for m in ctx
        )
        assert has_summary

    def test_lru_eviction(self, mem):
        mem._max_sessions = 3
        for i in range(5):
            mem.add_message(f"s{i}", "user", f"消息 {i}")

        assert len(mem._store) == 3
        assert "s0" not in mem._store
        assert "s1" not in mem._store
        assert "s4" in mem._store

    def test_clear_session(self, mem):
        mem.add_message("s5", "user", "你好")
        mem.clear("s5")
        assert "s5" not in mem._store

    def test_cleanup_expired(self, mem):
        import time
        mem.add_message("s6", "user", "消息")
        mem._store["s6"]["last_access"] = time.time() - config.memory.session_ttl - 10

        expired = mem.cleanup_expired()
        assert expired >= 1
        assert "s6" not in mem._store

    @pytest.mark.asyncio
    async def test_llm_summarizer_fallback(self, mem):
        async def failing_summarizer(messages):
            raise RuntimeError("LLM unavailable")

        mem.set_llm_summarizer(failing_summarizer)

        session_id = "s7"
        for i in range(config.memory.summary_threshold * 2 + 4):
            mem.add_message(session_id, "user", f"问题 {i}")
            mem.add_message(session_id, "assistant", f"回答 {i}")

        assert "s7" in mem._store
        assert len(mem._store["s7"]["messages"]) <= config.memory.window_size * 2

    def test_global_singleton(self):
        assert isinstance(memory_manager, ConversationMemory)
