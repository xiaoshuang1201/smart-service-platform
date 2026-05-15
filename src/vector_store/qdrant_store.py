"Qdrant 向量存储实现 (gRPC)"

from __future__ import annotations
import uuid

from qdrant_client import QdrantClient, grpc as qdrant_grpc
from qdrant_client.http import models as rest_models

from src.config import config
from src.vector_store.base import BaseVectorStore
from src.observability import logger


class QdrantVectorStore(BaseVectorStore):
    def __init__(self):
        self._client = QdrantClient(
            url=config.qdrant.url,
            api_key=config.qdrant.api_key or None,
            prefer_grpc=config.qdrant.prefer_grpc,
            port=config.qdrant.grpc_port if config.qdrant.prefer_grpc else 6333,
        )
        self._collection_name = config.qdrant.collection_name
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self._client.get_collection(self._collection_name)
        except Exception:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=rest_models.VectorParams(
                    size=config.qdrant.vector_size,
                    distance=rest_models.Distance.COSINE,
                ),
                hnsw_config=rest_models.HnswConfigDiff(
                    m=config.qdrant.hnsw_m,
                    ef_construct=config.qdrant.hnsw_ef_construct,
                ),
                quantization_config=rest_models.ScalarQuantization(
                    scalar=rest_models.ScalarQuantizationConfig(
                        type=rest_models.ScalarType.INT8,
                        quantile=0.99,
                        always_ram=True,
                    ),
                ),
            )
            logger.info("Qdrant collection created", collection=self._collection_name)

    async def index(self, chunks: list[dict], embeddings: list[list[float]]) -> int:
        points = [
            rest_models.PointStruct(
                id=chunk.get("id", str(uuid.uuid4())),
                vector=emb,
                payload={
                    "content": chunk["content"],
                    "metadata": chunk.get("metadata", {}),
                },
            )
            for chunk, emb in zip(chunks, embeddings)
        ]
        for i in range(0, len(points), 100):
            batch = points[i:i+100]
            self._client.upsert(
                collection_name=self._collection_name,
                points=batch,
                wait=True,
            )
        return len(points)

    async def search(
        self, query_embedding: list[float], top_k: int = 5,
        filters: dict | None = None
    ) -> list[dict]:
        search_filter = None
        if filters:
            conditions = []
            for k, v in filters.items():
                conditions.append(
                    rest_models.FieldCondition(
                        key=f"metadata.{k}",
                        match=rest_models.MatchValue(value=v),
                    )
                )
            if conditions:
                search_filter = rest_models.Filter(must=conditions)

        results = self._client.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )
        return [
            {
                "id": r.id,
                "content": r.payload.get("content", ""),
                "metadata": r.payload.get("metadata", {}),
                "score": r.score,
            }
            for r in results
        ]

    async def delete_by_doc_id(self, doc_id_base: str) -> int:
        results = self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="metadata.doc_id_base",
                        match=rest_models.MatchValue(value=doc_id_base),
                    )
                ]
            ),
            with_payload=False,
            limit=10000,
        )
        point_ids = [r.id for r in results[0]]
        if point_ids:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=rest_models.PointIdsList(points=point_ids),
                wait=True,
            )
        return len(point_ids)

    async def count(self) -> int:
        info = self._client.get_collection(self._collection_name)
        return info.points_count

    async def health_check(self) -> bool:
        try:
            self._client.get_collection(self._collection_name)
            return True
        except Exception:
            return False
