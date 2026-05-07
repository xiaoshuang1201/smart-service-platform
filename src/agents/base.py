# Agent 基类 — 统一日志、Token 统计、错误处理

from __future__ import annotations
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI

from src.config import config

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """所有 Agent 的抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self._llm = AsyncOpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            timeout=config.llm.timeout,
        )

    async def _call_llm(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> tuple[str, dict]:
        """统一的 LLM 调用封装，返回 (content, usage_info)"""
        t0 = time.time()
        temp = temperature if temperature is not None else config.llm.temperature
        mt = max_tokens if max_tokens is not None else config.llm.max_tokens

        kwargs = {
            "model": config.llm.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": mt,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            resp = await self._llm.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {e}")
            raise

        latency = (time.time() - t0) * 1000
        content = resp.choices[0].message.content or ""
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "total_tokens": resp.usage.total_tokens if resp.usage else 0,
            "latency_ms": int(latency),
        }

        logger.info(
            f"[{self.name}] LLM call: {usage['total_tokens']} tokens, "
            f"{usage['latency_ms']}ms"
        )
        return content, usage

    @abstractmethod
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行 Agent 逻辑，输入状态字典，返回更新后的状态字典"""
        ...
