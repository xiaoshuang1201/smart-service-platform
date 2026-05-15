"Celery async tasks — knowledge indexing, log processing"

import json
import asyncio

from src.queue import celery_app
from src.config import config
from src.observability import logger


@celery_app.task(name="knowledge.index", bind=True, max_retries=3, default_retry_delay=60)
def index_document(self, doc_id: str, minio_path: str, filename: str):
    """异步知识库文档索引"""
    logger.info("Starting document indexing", doc_id=doc_id, filename=filename)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _index():
        from src.storage.minio_client import MinioClient
        from src.rag.engine import chunk_documents, embedding_service
        from src.rag.engine import hybrid_retriever

        minio = MinioClient()
        local_path = f"/tmp/{doc_id}_{filename}"
        await minio.download_file(minio_path, local_path)

        chunks = chunk_documents(local_path)
        if not chunks:
            logger.warning("No text extracted from document", doc_id=doc_id)
            return {"status": "empty", "chunks": 0}

        texts = [c["content"] for c in chunks]
        embeddings = await embedding_service.embed_texts(texts)

        from src.rag.engine import vector_store
        count = vector_store.index_chunks(chunks, embeddings)
        hybrid_retriever.build_bm25(chunks)

        import os
        os.unlink(local_path)
        logger.info("Document indexing complete", doc_id=doc_id, chunks=count)
        return {"status": "success", "chunks": count}

    return loop.run_until_complete(_index())


@celery_app.task(name="log.process", bind=True, max_retries=1)
def process_conversation_log(self, conversation_id: str, trace_data: dict):
    """异步对话日志持久化到 PostgreSQL"""
    async def _save():
        from src.db.session import AsyncSessionLocal
        from src.db.models import Conversation, Message, ToolCall
        from sqlalchemy import select
        import uuid

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
            )
            conv = result.scalar_one_or_none()
            if conv:
                conv.metadata_ = {**conv.metadata_, "trace": trace_data}
        return True
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_save())


@celery_app.task(name="cleanup.expired", bind=True)
def cleanup_expired_sessions(self):
    """定期清理过期 Redis 会话"""
    from src.memory.redis_memory import get_memory_backend
    from src.memory.conversation_memory import memory_manager
    try:
        count = memory_manager.cleanup_expired()
        logger.info("Expired sessions cleaned", count=count)
        return count
    except Exception as e:
        logger.error("Session cleanup failed", error=str(e))
        return 0
