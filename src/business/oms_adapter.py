"OMS 订单系统适配器"

from __future__ import annotations
import asyncio
import json
from typing import Any

import httpx

from src.config import config
from src.business.base import BaseBusinessAdapter
from src.observability import logger


MOCK_ORDERS = {
    "20260507001": {
        "status": "运输中", "carrier": "顺丰速运", "eta": "2026-05-09",
        "items": [{"name": "蓝牙耳机", "qty": 1, "price": 299.0}],
        "total": 299.0, "address": "北京市朝阳区XX路XX号",
    },
    "20260506001": {
        "status": "已签收", "carrier": "中通快递", "eta": "已送达",
        "items": [{"name": "手机壳", "qty": 2, "price": 39.9}],
        "total": 79.8, "address": "上海市浦东新区XX大厦",
    },
    "20260505001": {
        "status": "待发货", "carrier": None, "eta": "预计5月8日发货",
        "items": [{"name": "机械键盘", "qty": 1, "price": 599.0}],
        "total": 599.0, "address": "杭州市西湖区XX科技园",
    },
}


class OMSAdapter(BaseBusinessAdapter):
    name = "oms"

    def __init__(self):
        self._vendor = config.oms.vendor

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        order_id = params.get("order_id", "")
        if self._vendor == "mock":
            return await self._mock_query(order_id)
        else:
            return await self._http_query(order_id)

    async def _mock_query(self, order_id: str) -> dict:
        await asyncio.sleep(0.3)
        order = MOCK_ORDERS.get(order_id)
        if not order:
            return {
                "found": False, "order_id": order_id,
                "message": f"未找到订单 {order_id}，请确认订单号是否正确",
            }
        return {"found": True, "order_id": order_id, **order}

    async def _http_query(self, order_id: str) -> dict:
        from src.business.resilience import resilient_call

        async def _call():
            async with httpx.AsyncClient(timeout=config.oms.timeout) as client:
                resp = await client.get(
                    f"{config.oms.base_url}/orders/{order_id}",
                    headers={"Authorization": f"Bearer {config.oms.api_key}"},
                )
                resp.raise_for_status()
                return resp.json()

        async def _fallback(order_id: str):
            logger.warning("OMS unavailable, using mock fallback")
            return await self._mock_query(order_id)

        return await resilient_call(
            _call,
            retry_attempts=config.oms.max_retries,
            backoff=config.oms.retry_backoff,
            timeout=config.oms.timeout,
            circuit_breaker_name="oms",
            fallback_fn=_fallback,
        )

    async def health_check(self) -> bool:
        if self._vendor == "mock":
            return True
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{config.oms.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
