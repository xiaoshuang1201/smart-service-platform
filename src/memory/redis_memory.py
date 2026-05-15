"Redis-backed conversation memory with Sentinel/Cluster support"

from __future__ import annotations
import json
import time
import asyncio
from typing import Any, Callable

import redis.asyncio as aioredis
from redis.asyncio.sentinel import Sentinel

from src.config import config
from src.observability import logger


def _build_redis() -> aioredis.Redis:
    backend = config.memory.redis_backend
    password = config.memory.redis_password or None
    if backend == "sentinel":
        sentinel_hosts = [
            tuple(h.split(":")) for h in
            os.getenv("REDIS_SENTINEL_HOSTS", "localhost:26379").split(",")
        ]
        sentinel_hosts = [(h, int(p)) for h, p in sentinel_hosts]
        sentinel = Sentinel(sentinel_hosts, socket_timeout=2.0)
        return sentinel.master_for(
            config.memory.redis_sentinel_master,
            password=password,
            decode_responses=False,
        )
    elif backend == "cluster":
        from redis.cluster import RedisCluster
        # aioredis doesn't have RedisCluster; use strict mode
        url = config.memory.redis_url
        return aioredis.from_url(url, password=password, decode_responses=False)
    else:
        url = config.memory.redis_url
        return aioredis.from_url(url, password=password, decode_responses=False)


import os


class RedisConversationMemory:
    """Redis-backed conversation memory with in-memory fallback"""

    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._fallback_store: dict[str, dict] = {}
        self._connected = False
        self._max_sessions = 1000

    async def _ensure_redis(self) -> aioredis.Redis | None:
        if self._redis is not None:
            return self._redis
        try:
            self._redis = _build_redis()
            await self._redis.ping()
            self._connected = True
            logger.info("Redis connected", backend=config.memory.redis_backend)
            return self._redis
        except Exception as e:
            logger.warning("Redis unavailable, using in-memory fallback", error=str(e))
            self._connected = False
            self._redis = None
            return None

    def _session_key(self, session_id: str) -> str:
        return f"sm:session:{session_id}"

    def _msg_key(self, session_id: str) -> str:
        return f"sm:messages:{session_id}"

    async def get_or_create_session(self, session_id: str) -> dict:
        redis = await self._ensure_redis()
        if redis:
            key = self._session_key(session_id)
            exists = await redis.exists(key)
            if not exists:
                await redis.hset(key, mapping={
                    "summary": "",
                    "created_at": str(time.time()),
                    "last_access": str(time.time()),
                })
                await redis.expire(key, config.memory.session_ttl)
            await redis.hset(key, "last_access", str(time.time()))
            return {"summary": "", "created_at": time.time(), "last_access": time.time()}
        else:
            return self._fallback_get_or_create(session_id)

    def _fallback_get_or_create(self, session_id: str) -> dict:
        if session_id not in self._fallback_store:
            if len(self._fallback_store) >= self._max_sessions:
                oldest = next(iter(self._fallback_store))
                del self._fallback_store[oldest]
            self._fallback_store[session_id] = {
                "messages": [],
                "summary": "",
                "created_at": time.time(),
                "last_access": time.time(),
            }
        self._fallback_store[session_id]["last_access"] = time.time()
        return self._fallback_store[session_id]

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        redis = await self._ensure_redis()
        if redis:
            msg = json.dumps({
                "role": role,
                "content": content,
                "timestamp": time.time(),
            }, ensure_ascii=False)
            key = self._msg_key(session_id)
            await redis.rpush(key, msg)
            await redis.ltrim(key, -(config.memory.window_size * 2 * 3), -1)
            await redis.expire(key, config.memory.session_ttl)
            await redis.hset(self._session_key(session_id), "last_access", str(time.time()))
            await redis.expire(self._session_key(session_id), config.memory.session_ttl)
        else:
            self._fallback_add_message(session_id, role, content)

    def _fallback_add_message(self, session_id: str, role: str, content: str) -> None:
        session = self._fallback_get_or_create(session_id)
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        if len(session["messages"]) > config.memory.summary_threshold * 2:
            keep = config.memory.window_size * 2
            old_msgs = session["messages"][:-keep]
            if old_msgs:
                parts = [f"用户问: {m['content'][:80]}" for m in old_msgs[-10:] if m["role"] == "user"]
                session["summary"] = "；".join(parts) if parts else session["summary"]
                session["messages"] = session["messages"][-keep:]

    async def get_context(self, session_id: str, n: int | None = None) -> list[dict]:
        if n is None:
            n = config.memory.window_size * 2
        redis = await self._ensure_redis()
        if redis:
            key = self._msg_key(session_id)
            raw_msgs = await redis.lrange(key, -n, -1)
            context = []
            summary = await redis.hget(self._session_key(session_id), "summary")
            if summary:
                summary_text = summary.decode("utf-8") if isinstance(summary, bytes) else summary
                if summary_text:
                    context.append({"role": "system", "content": f"[对话历史摘要] {summary_text}"})
            for raw in raw_msgs:
                raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                try:
                    context.append(json.loads(raw_text))
                except json.JSONDecodeError:
                    context.append({"role": "assistant", "content": raw_text})
            return context
        else:
            return self._fallback_get_context(session_id, n)

    def _fallback_get_context(self, session_id: str, n: int) -> list[dict]:
        session = self._fallback_store.get(session_id, {"messages": [], "summary": ""})
        recent = session["messages"][-n:]
        context = []
        if session.get("summary"):
            context.append({"role": "system", "content": f"[对话历史摘要] {session['summary']}"})
        context.extend(recent)
        return context

    async def clear(self, session_id: str) -> None:
        redis = await self._ensure_redis()
        if redis:
            await redis.delete(self._session_key(session_id), self._msg_key(session_id))
        else:
            self._fallback_store.pop(session_id, None)

    async def is_connected(self) -> bool:
        if self._redis is None:
            await self._ensure_redis()
        return self._connected


# Global singleton factory
_global_memory: RedisConversationMemory | None = None


def get_memory_backend() -> RedisConversationMemory:
    global _global_memory
    if _global_memory is None:
        _global_memory = RedisConversationMemory()
    return _global_memory
