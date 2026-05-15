#!/usr/bin/env python3
"数据库初始化 — 创建所有表"

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.models import Base
from src.db.session import engine


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] All database tables created successfully")


if __name__ == "__main__":
    asyncio.run(init())
