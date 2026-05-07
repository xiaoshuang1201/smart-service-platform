# RAG 引擎 — 文档加载、分块、向量化存储、混合检索

from __future__ import annotations
import asyncio
import hashlib
import re
from pathlib import Path
from typing import AsyncIterator, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredMarkdownLoader,
    Docx2txtLoader, CSVLoader,
)
import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np
from openai import AsyncOpenAI

from src.config import config


# ─── 文档加载器 ──────────────────────────────────────

LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".docx": Docx2txtLoader,
    ".csv": CSVLoader,
    ".html": TextLoader,
}

SUPPORTED_EXTENSIONS = set(LOADER_MAP.keys())

def _detect_file_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")
    return ext

def _compute_doc_id(file_path: str) -> str:
    """基于文件内容哈希生成唯一文档 ID"""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:16]

# ─── 文档分块 ────────────────────────────────────────

def chunk_documents(file_path: str) -> list[dict]:
    """加载文档并智能分块"""
    ext = _detect_file_type(file_path)
    LoaderCls = LOADER_MAP[ext]
    loader = LoaderCls(file_path)
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.rag.chunk_size,
        chunk_overlap=config.rag.chunk_overlap,
        separators=["\n## ", "\n### ", "\n#### ", "\n", "。", ". ", "；", ";", "，", ", ", " ", ""],
        keep_separator=True,
    )

    chunks = []
    doc_id_base = _compute_doc_id(file_path)
    filename = Path(file_path).name

    for i, chunk in enumerate(splitter.split_documents(raw_docs)):
        chunks.append({
            "id": f"{doc_id_base}_chunk_{i:04d}",
            "content": chunk.page_content.strip(),
            "metadata": {
                "filename": filename,
                "chunk_index": i,
                "doc_id_base": doc_id_base,
                "source": chunk.metadata.get("source", ""),
                "page": chunk.metadata.get("page", -1),
            }
        })

    return chunks

# ─── Embedding 生成 ──────────────────────────────────

class EmbeddingService:
    """基于 DashScope text-embedding-v3 的向量化服务"""

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=config.embedding.api_key,
            base_url=config.llm.base_url,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for i in range(0, len(texts), config.embedding.batch_size):
            batch = texts[i : i + config.embedding.batch_size]
            resp = await self._client.embeddings.create(
                model=config.embedding.model,
                input=batch,
            )
            embeddings.extend([d.embedding for d in resp.data])
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(
            model=config.embedding.model,
            input=[text],
        )
        return resp.data[0].embedding


embedding_service = EmbeddingService()

# ─── 向量存储操作 ────────────────────────────────────

class VectorStore:
    """ChromaDB 向量存储封装"""

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=config.vector_db.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=config.vector_db.collection_name,
            metadata={"hnsw:space": config.vector_db.distance_metric},
        )

    def index_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> int:
        """将分块及其向量写入 ChromaDB"""
        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # 分批写入，避免单次写入过大
        batch_size = 100
        total = 0
        for i in range(0, len(ids), batch_size):
            self._collection.add(
                ids=ids[i : i + batch_size],
                embeddings=embeddings[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )
            total += len(ids[i : i + batch_size])
        return total

    def search(
        self,
        query_embedding: list[float],
        top_k: Optional[int] = None,
    ) -> list[dict]:
        """向量检索"""
        if top_k is None:
            top_k = config.rag.top_k
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return _format_results(results)

    def delete_by_doc_id(self, doc_id_base: str) -> int:
        """按文档 ID 删除所有相关分块"""
        results = self._collection.get(
            where={"doc_id_base": doc_id_base},
            include=[],
        )
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
        return len(results["ids"])

    def count(self) -> int:
        return self._collection.count()


def _format_results(raw: dict) -> list[dict]:
    """将 ChromaDB 返回结果格式化为统一结构"""
    formatted = []
    if not raw["ids"] or not raw["ids"][0]:
        return formatted
    for i, chunk_id in enumerate(raw["ids"][0]):
        formatted.append({
            "id": chunk_id,
            "content": raw["documents"][0][i] if raw["documents"] else "",
            "metadata": raw["metadatas"][0][i] if raw["metadatas"] else {},
            "score": 1 - raw["distances"][0][i] if raw["distances"] else 0,
        })
    return formatted

# ─── BM25 关键词检索 ─────────────────────────────────

class BM25Retriever:
    """基于jieba分词的BM25关键词检索（轻量级实现）"""

    def __init__(self):
        self._corpus: list[str] = []
        self._chunks: list[dict] = []

    def build_index(self, chunks: list[dict]):
        self._chunks = chunks
        self._corpus = [c["content"] for c in chunks]

    def _tokenize(self, text: str) -> list[str]:
        try:
            import jieba
            return list(jieba.cut(text))
        except ImportError:
            return re.findall(r"[一-鿿]+|[a-zA-Z]+", text)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """简单的 TF-IDF 相似度计算"""
        if not self._corpus:
            return []
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return []

        scores = []
        for i, doc in enumerate(self._corpus):
            doc_tokens = self._tokenize(doc)
            # 简单的共现比例得分
            overlap = len(set(doc_tokens) & query_tokens)
            score = overlap / (len(query_tokens) + 1e-8) if doc_tokens else 0
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scores[:top_k]:
            if score > 0:
                chunk = self._chunks[idx].copy()
                chunk["score"] = score
                results.append(chunk)
        return results

# ─── 混合检索器 ──────────────────────────────────────

class HybridRetriever:
    """向量检索 + BM25 + Reranker 的混合检索管道"""

    def __init__(self, vector_store: VectorStore):
        self._vs = vector_store
        self._bm25 = BM25Retriever()

    @property
    def bm25(self) -> BM25Retriever:
        return self._bm25

    def build_bm25(self, chunks: list[dict]):
        self._bm25.build_index(chunks)

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        # 1. 向量检索
        q_emb = await embedding_service.embed_query(query)
        vector_results = self._vs.search(q_emb, top_k=top_k * 2)

        # 2. BM25 检索（如果启用）
        bm25_results = []
        if config.rag.hybrid_search_enabled:
            bm25_results = self._bm25.search(query, top_k=top_k)

        # 3. RRF (Reciprocal Rank Fusion) 合并排序
        merged = _rrf_merge(
            vector_results, bm25_results,
            bm25_weight=config.rag.bm25_weight,
            top_k=top_k,
        )

        # 4. 过滤低相似度结果
        merged = [r for r in merged if r["score"] >= config.rag.similarity_threshold]

        return merged[:top_k]


def _rrf_merge(
    vector_results: list[dict],
    bm25_results: list[dict],
    bm25_weight: float = 0.3,
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion — 融合向量和BM25的排序结果"""
    scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}

    for rank, r in enumerate(vector_results):
        scores[r["id"]] = (1.0 - bm25_weight) / (k + rank + 1)
        chunk_map[r["id"]] = r

    for rank, r in enumerate(bm25_results):
        bonus = bm25_weight / (k + rank + 1)
        scores[r["id"]] = scores.get(r["id"], 0) + bonus
        if r["id"] not in chunk_map:
            chunk_map[r["id"]] = r

    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    merged = []
    for cid in sorted_ids:
        chunk = chunk_map[cid].copy()
        chunk["score"] = scores[cid]
        merged.append(chunk)

    return merged


# ─── 全局实例 ────────────────────────────────────────

vector_store = VectorStore()
hybrid_retriever = HybridRetriever(vector_store)
