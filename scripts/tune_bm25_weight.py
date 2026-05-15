#!/usr/bin/env python3
"BM25 权重调优脚本 — 在标注数据上评估不同权重的检索效果"
#
# 用法: python scripts/tune_bm25_weight.py
# TODO: 需要人工标注的测试集 (query -> relevant_chunk_ids)，目前使用示例数据演示流程

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.rag.engine import hybrid_retriever, embedding_service, vector_store


TEST_QUERIES = [
    ("如何申请退货退款？", ["chunk_0"]),
    ("订单什么时候发货？", ["chunk_1"]),
    ("客服电话是多少？", ["chunk_2"]),
    ("会员等级有哪些权益？", ["chunk_3"]),
    ("在哪里领取优惠券？", ["chunk_4"]),
]

WEIGHTS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]


def evaluate_weight(weight: float, results_by_query: dict) -> dict:
    """计算单个权重下的 MRR 和 Recall@3"""
    mrr_total = 0.0
    recall_total = 0.0
    n = len(TEST_QUERIES)

    for query, relevant_ids in TEST_QUERIES:
        retrieved = results_by_query.get(query, {}).get(str(weight), [])
        retrieved_ids = [r["id"] for r in retrieved]

        # MRR
        for rank, rid in enumerate(retrieved_ids):
            if rid in relevant_ids:
                mrr_total += 1.0 / (rank + 1)
                break

        # Recall@3
        hits = sum(1 for rid in retrieved_ids[:3] if rid in relevant_ids)
        recall_total += hits / len(relevant_ids) if relevant_ids else 0.0

    return {
        "weight": weight,
        "mrr": round(mrr_total / n, 4),
        "recall_at_3": round(recall_total / n, 4),
    }


async def main():
    print("=" * 60)
    print("BM25 权重调优")
    print(f"向量库: {vector_store.count()} 个分块")
    print(f"测试查询: {len(TEST_QUERIES)} 条")
    print("=" * 60)

    results_by_query = {}

    for query, _ in TEST_QUERIES:
        results_by_query[query] = {}
        for w in WEIGHTS:
            config.rag.bm25_weight = w
            results = await hybrid_retriever.retrieve(query, top_k=5)
            results_by_query[query][str(w)] = results

    print(f"\n{'权重':>6}  {'MRR':>8}  {'Recall@3':>10}")
    print("-" * 32)

    best_weight = 0.3
    best_mrr = 0.0

    for w in WEIGHTS:
        metrics = evaluate_weight(w, results_by_query)
        print(f"{metrics['weight']:>6.1f}  {metrics['mrr']:>8.4f}  {metrics['recall_at_3']:>10.4f}")
        if metrics["mrr"] > best_mrr:
            best_mrr = metrics["mrr"]
            best_weight = w

    print("-" * 32)
    print(f"\n推荐 BM25 权重: {best_weight} (MRR={best_mrr})")
    print(f"当前配置权重: {config.rag.bm25_weight}")
    print("\n设置方式: export BM25_WEIGHT={}".format(best_weight))


if __name__ == "__main__":
    asyncio.run(main())
