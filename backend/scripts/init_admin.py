"""
创建初始管理员账号脚本
用法: ADMIN_PASSWORD=<strong-password> python scripts/init_admin.py [username]
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.utils.auth import get_password_hash


async def create_admin_user():
    admin_username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_password or len(admin_password) < 8:
        print("错误: 请通过环境变量 ADMIN_PASSWORD 设置至少 8 位的密码")
        print("用法: ADMIN_PASSWORD=<密码> python scripts/init_admin.py [用户名]")
        sys.exit(1)

    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.username == admin_username)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"管理员账号 '{admin_username}' 已存在")
            return

        admin_user = User(
            username=admin_username,
            password_hash=get_password_hash(admin_password),
            role="admin"
        )
        session.add(admin_user)
        await session.commit()

        print(f"管理员账号创建成功: {admin_username}")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
