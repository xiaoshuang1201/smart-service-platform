"抽象业务适配器接口"

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseBusinessAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
