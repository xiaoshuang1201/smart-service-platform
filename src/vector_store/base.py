"抽象向量存储接口"

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseVectorStore(ABC):
    @abstractmethod
    async def index(self, chunks: list[dict], embeddings: list[list[float]]) -> int: ...

    @abstractmethod
    async def search(
        self, query_embedding: list[float], top_k: int = 5,
        filters: dict | None = None
    ) -> list[dict]: ...

    @abstractmethod
    async def delete_by_doc_id(self, doc_id_base: str) -> int: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
