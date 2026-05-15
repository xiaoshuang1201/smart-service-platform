"CRM 会员系统适配器"

from __future__ import annotations
import asyncio
import hashlib
from typing import Any

import httpx

from src.config import config
from src.business.base import BaseBusinessAdapter
from src.observability import logger


MOCK_CRM = {
    "13800001111": {
        "name": "张先生", "level": "金牌会员", "points": 12800,
        "total_orders": 47, "join_date": "2023-03-15",
        "last_order": "2026-05-01", "preferences": ["数码", "家居"],
    },
    "13900002222": {
        "name": "李女士", "level": "银牌会员", "points": 3200,
        "total_orders": 12, "join_date": "2025-06-20",
        "last_order": "2026-04-15", "preferences": ["美妆", "母婴"],
    },
}


def _mask_phone(phone: str) -> str:
    return phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else phone


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()


class CRMAdapter(BaseBusinessAdapter):
    name = "crm"

    def __init__(self):
        self._vendor = config.crm.vendor

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        phone = params.get("phone", "")
        if self._vendor == "mock":
            return await self._mock_lookup(phone)
        else:
            return await self._http_lookup(phone)

    async def _mock_lookup(self, phone: str) -> dict:
        await asyncio.sleep(0.25)
        masked = _mask_phone(phone)
        user = MOCK_CRM.get(phone)
        if not user:
            return {
                "found": False, "phone": masked,
                "message": "未找到该用户信息，建议引导用户注册会员",
            }
        return {"found": True, "phone": masked, **user}

    async def _http_lookup(self, phone: str) -> dict:
        from src.business.resilience import resilient_call
        phone_hashed = _hash_phone(phone)
        masked = _mask_phone(phone)

        async def _call():
            async with httpx.AsyncClient(timeout=config.crm.timeout) as client:
                resp = await client.get(
                    f"{config.crm.base_url}/members/{phone_hashed}",
                    headers={"Authorization": f"Bearer {config.crm.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                data["phone"] = masked
                return data

        async def _fallback(phone: str):
            logger.warning("CRM unavailable, using mock fallback")
            return await self._mock_lookup(phone)

        return await resilient_call(
            _call,
            retry_attempts=config.crm.max_retries,
            backoff=config.crm.retry_backoff,
            timeout=config.crm.timeout,
            circuit_breaker_name="crm",
            fallback_fn=_fallback,
        )

    async def health_check(self) -> bool:
        if self._vendor == "mock":
            return True
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{config.crm.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
