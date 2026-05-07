# FastAPI 接口集成测试

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from src.main import app


@pytest.fixture
def api_key_headers():
    return {"X-API-Key": "sk-demo-key"}


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["service"] == "SmartService"


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_sync_with_valid_key(self):
        """同步对话接口 — 集成测试"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat/send-sync",
                json={
                    "message": "如何退货？",
                    "user_id": "test_user_001",
                },
                headers={"X-API-Key": "sk-demo-key"},
                timeout=60,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "response" in data
            assert "trace_id" in data
            assert "session_id" in data
            assert "total_latency_ms" in data

    @pytest.mark.asyncio
    async def test_chat_without_api_key_returns_401(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat/send-sync",
                json={"message": "test"},
            )
            assert resp.status_code == 401


class TestKnowledgeEndpoint:
    @pytest.mark.asyncio
    async def test_knowledge_health(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/knowledge/health",
                headers={"X-API-Key": "sk-demo-key"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "total_chunks" in data
            assert "status" in data


class TestChatSSE:
    @pytest.mark.asyncio
    async def test_chat_sse_returns_events(self):
        """SSE 流式接口 — 返回格式正确"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat/send",
                json={
                    "message": "查询订单20260507001",
                    "user_id": "test_user_002",
                },
                headers={"X-API-Key": "sk-demo-key"},
                timeout=60,
            )
            assert resp.status_code == 200
            # SSE响应应该是 text/event-stream
            assert "text/event-stream" in resp.headers.get("content-type", "")

            body = resp.text
            assert "event:" in body
            assert "data:" in body
