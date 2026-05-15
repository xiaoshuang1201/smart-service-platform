# FastAPI 路由 — 对话、知识库、管理接口

from __future__ import annotations
import asyncio
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, status
from fastapi.responses import StreamingResponse

from src.workflow.graph import run_orchestrator
from src.rag.engine import chunk_documents, embedding_service, vector_store, hybrid_retriever
from src.models.schemas import ChatRequest, KnowledgeHealth, DocumentInfo, ChatEvent
from src.config import config
from src.security.guard import InputGuard
from src.observability import logger, set_trace_id
from src.observability.metrics import (
    chat_request_total, chat_request_duration_seconds,
)

router = APIRouter(prefix="/api/v1")
_input_guard = InputGuard()
router = APIRouter(prefix="/api/v1")


# ─── 鉴权依赖 ────────────────────────────────────────

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != config.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return x_api_key


# ─── 对话接口 ────────────────────────────────────────

@router.post("/chat/send")
async def chat_send(
    req: ChatRequest,
    api_key: str = Depends(verify_api_key),
):
    """发送消息 — SSE 流式返回 Agent 处理过程和最终结果"""
    check = _input_guard.check(req.message, req.user_id)
    if not check.allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=check.reason)

    async def event_stream():
        try:
            result = await run_orchestrator(
                user_message=check.sanitized,
                session_id=req.conversation_id,
                user_id=req.user_id,
            )
        except Exception:
            logger.exception("Chat SSE pipeline failed")
            yield _sse_event("error", {"message": "系统处理异常，请稍后重试"}, "error")
            yield _sse_event("done", {"should_escalate": True}, "error")
            return

        trace_id = result["trace_id"]
        set_trace_id(trace_id)

        if result.get("intent"):
            intent = result["intent"]
            yield _sse_event("intent", {
                "intent": intent.intent,
                "sentiment": intent.sentiment,
                "confidence": intent.confidence,
            }, trace_id)

        for tc in result.get("tool_calls", []):
            yield _sse_event("tool_call", {
                "tool_name": tc.get("tool_name"),
                "status": tc.get("status"),
            }, trace_id)

        response_text = result["response"]
        for i in range(0, len(response_text), 8):
            chunk = response_text[i:i+8]
            yield _sse_event("token", {"text": chunk}, trace_id)
            await asyncio.sleep(0.01)

        yield _sse_event("done", {
            "session_id": result["session_id"],
            "confidence": result["confidence"],
            "total_latency_ms": result["total_latency_ms"],
            "total_tokens": result["total_tokens"],
        }, trace_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/send-sync")
async def chat_send_sync(
    req: ChatRequest,
    api_key: str = Depends(verify_api_key),
):
    """同步接口 — 一次性返回完整结果"""
    check = _input_guard.check(req.message, req.user_id)
    if not check.allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=check.reason)
    return await run_orchestrator(
        user_message=check.sanitized,
        session_id=req.conversation_id,
        user_id=req.user_id,
    )


# ─── 知识库接口 ────────────────────────────────────────

@router.post("/knowledge/upload")
async def knowledge_upload(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
):
    """上传文档到知识库"""
    # 1. 保存临时文件
    import tempfile, os
    suffix = os.path.splitext(file.filename or "doc.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 2. 分块
        chunks = chunk_documents(tmp_path)
        if not chunks:
            return {"status": "error", "message": "文档无可提取的文本内容"}

        # 3. 向量化
        texts = [c["content"] for c in chunks]
        embeddings = await embedding_service.embed_texts(texts)

        # 4. 写入向量库
        count = vector_store.index_chunks(chunks, embeddings)

        # 5. 更新 BM25 索引
        hybrid_retriever.build_bm25(chunks)

        return {
            "status": "success",
            "filename": file.filename,
            "chunk_count": count,
            "message": f"成功索引 {count} 个文档片段",
        }
    finally:
        os.unlink(tmp_path)


@router.get("/knowledge/health", response_model=KnowledgeHealth)
async def knowledge_health(api_key: str = Depends(verify_api_key)):
    """知识库健康检查"""
    total_chunks = vector_store.count()
    return KnowledgeHealth(
        total_documents=0,  # 简化版
        total_chunks=total_chunks,
        collection_name=config.vector_db.collection_name,
        status="healthy" if total_chunks > 0 else "degraded",
    )


# ─── 管理接口 ────────────────────────────────────────

@router.get("/admin/health")
async def health_check():
    return {
        "status": "ok",
        "version": config.version,
        "service": config.app_name,
    }


@router.get("/admin/stats")
async def admin_stats(api_key: str = Depends(verify_api_key)):
    """运营数据统计"""
    total_chunks = vector_store.count()
    return {
        "knowledge_base": {
            "total_chunks": total_chunks,
            "collection": config.vector_db.collection_name,
        },
        "config": {
            "llm_model": config.llm.model,
            "embedding_model": config.embedding.model,
            "rag_top_k": config.rag.top_k,
            "chunk_size": config.rag.chunk_size,
        },
    }


def _sse_event(event: str, data: dict, trace_id: str) -> str:
    """格式化 SSE 事件"""
    payload = json.dumps({"event": event, "data": data, "trace_id": trace_id}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
