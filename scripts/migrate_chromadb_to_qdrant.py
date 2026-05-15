#!/usr/bin/env python3
"Chromadb → Qdrant 迁移脚本"

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.engine import vector_store as old_store, chunk_documents
from src.vector_store.qdrant_store import QdrantVectorStore
from src.config import config
from src.observability import logger


async def migrate():
    qdrant = QdrantVectorStore()

    old_count = old_store.count()
    logger.info(f"Source (Chromadb): {old_count} chunks")

    if old_count == 0:
        logger.info("No chunks to migrate, skipping")
        return

    # ChromaDB iteration is sync; collect all chunks
    results = old_store._collection.get(include=["documents", "metadatas", "embeddings"])
    if not results["ids"]:
        logger.warning("No data found in ChromaDB")
        return

    chunks = []
    embeddings = []
    for i, chunk_id in enumerate(results["ids"]):
        chunks.append({
            "id": chunk_id,
            "content": results["documents"][i] if results["documents"] else "",
            "metadata": results["metadatas"][i] if results["metadatas"] else {},
        })
        if results.get("embeddings") and results["embeddings"][i]:
            embeddings.append(results["embeddings"][i])

    # If embeddings not in ChromaDB, regenerate
    if not embeddings:
        logger.warning("No embeddings in ChromaDB, regenerating...")
        from src.rag.engine import embedding_service
        texts = [c["content"] for c in chunks]
        embeddings = await embedding_service.embed_texts(texts)

    count = await qdrant.index(chunks, embeddings)
    new_count = await qdrant.count()

    logger.info(f"Migration complete: {old_count} -> {new_count} chunks in Qdrant")
    assert new_count >= old_count, f"Count mismatch: {old_count} vs {new_count}"


if __name__ == "__main__":
    asyncio.run(migrate())
