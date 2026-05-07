# 工具注册中心 — 统一管理和发现可用工具

from __future__ import annotations
from typing import Any, Protocol

class Tool(Protocol):
    """工具接口协议"""
    name: str
    description: str
    params_schema: dict[str, Any]

    async def execute(self, **kwargs) -> Any:
        ...

class ToolRegistry:
    """工具注册中心 — 注册、查找、列举所有可用工具"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_all(self) -> list[str]:
        return list(self._tools.keys())

    def describe_all(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "params": t.params_schema,
            }
            for t in self._tools.values()
        ]

# 全局单例
tool_registry = ToolRegistry()
