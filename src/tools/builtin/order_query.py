# 订单查询工具 — 模拟企业订单系统 API

from __future__ import annotations
import asyncio
import random
from typing import Any

MOCK_ORDERS = {
    "20260507001": {"status": "运输中", "carrier": "顺丰速运", "eta": "2026-05-09",
                     "items": [{"name": "蓝牙耳机", "qty": 1, "price": 299.0}],
                     "total": 299.0, "address": "北京市朝阳区XX路XX号"},
    "20260506001": {"status": "已签收", "carrier": "中通快递", "eta": "已送达",
                     "items": [{"name": "手机壳", "qty": 2, "price": 39.9}],
                     "total": 79.8, "address": "上海市浦东新区XX大厦"},
    "20260505001": {"status": "待发货", "carrier": None, "eta": "预计5月8日发货",
                     "items": [{"name": "机械键盘", "qty": 1, "price": 599.0}],
                     "total": 599.0, "address": "杭州市西湖区XX科技园"},
}

class OrderQueryTool:
    name = "order_query"
    description = "根据订单号查询订单状态、物流信息、商品明细"
    params_schema = {"order_id": {"type": "string", "required": True, "description": "10位以上数字订单号"}}

    async def execute(self, order_id: str, **kwargs) -> Any:
        await asyncio.sleep(0.3)  # 模拟 API 延迟

        order = MOCK_ORDERS.get(order_id)
        if not order:
            return {"found": False, "order_id": order_id,
                    "message": f"未找到订单 {order_id}，请确认订单号是否正确"}
        return {"found": True, "order_id": order_id, **order}
