"""
创建初始管理员账号脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.utils.auth import get_password_hash


async def create_admin_user():
    """创建初始管理员账号"""
    # 初始化数据库
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # 检查是否已存在管理员
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print("管理员账号已存在")
            return
        
        # 创建管理员账号
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),  # 默认密码，生产环境需修改
            role="admin"
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("✓ 管理员账号创建成功")
        print("  用户名: admin")
        print("  密码: admin123")
        print("  ⚠️  请在生产环境中修改默认密码！")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
