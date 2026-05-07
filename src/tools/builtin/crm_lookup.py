# CRM 查询工具 — 模拟企业 CRM 系统

from __future__ import annotations
import asyncio
from typing import Any

MOCK_CRM = {
    "13800001111": {"name": "张先生", "level": "金牌会员", "points": 12800,
                     "total_orders": 47, "join_date": "2023-03-15",
                     "last_order": "2026-05-01", "preferences": ["数码", "家居"]},
    "13900002222": {"name": "李女士", "level": "银牌会员", "points": 3200,
                     "total_orders": 12, "join_date": "2025-06-20",
                     "last_order": "2026-04-15", "preferences": ["美妆", "母婴"]},
}

class CRMLookupTool:
    name = "crm_lookup"
    description = "根据手机号查询会员等级、积分、购买历史"
    params_schema = {"phone": {"type": "string", "required": True, "description": "11 位手机号码"}}

    async def execute(self, phone: str, **kwargs) -> Any:
        await asyncio.sleep(0.25)

        # PII 脱敏处理
        masked = phone[:3] + "****" + phone[-4:]

        user = MOCK_CRM.get(phone)
        if not user:
            return {"found": False, "phone": masked,
                    "message": "未找到该用户信息，建议引导用户注册会员"}
        return {"found": True, "phone": masked, **user}
