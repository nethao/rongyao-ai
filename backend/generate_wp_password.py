#!/usr/bin/env python3
"""
为WordPress用户生成应用程序密码
"""
import asyncio
import hashlib
import secrets
import string
from datetime import datetime


async def generate_app_password():
    """生成WordPress应用程序密码"""
    
    # 生成24字符的随机密码
    alphabet = string.ascii_letters + string.digits
    raw_password = ''.join(secrets.choice(alphabet) for _ in range(24))
    
    # 格式化为WordPress格式（每4个字符一组，用空格分隔）
    formatted_password = ' '.join([raw_password[i:i+4] for i in range(0, len(raw_password), 4)])
    
    # 生成WordPress密码哈希（使用phpass算法）
    # 注意：这里简化处理，实际应该使用WordPress的wp_hash_password函数
    # 对于测试，我们使用一个已知的测试密码
    
    print("=" * 60)
    print("WordPress应用程序密码生成器")
    print("=" * 60)
    print(f"\n生成的应用程序密码：")
    print(f"{formatted_password}")
    print(f"\n原始密码（用于API调用）：")
    print(f"{raw_password}")
    print("\n" + "=" * 60)
    print("使用说明：")
    print("=" * 60)
    print("\n1. 访问 WordPress 后台")
    print("2. 进入 用户 -> 个人资料")
    print("3. 找到 '应用程序密码' 部分")
    print("4. 手动创建一个应用程序密码")
    print("5. 将生成的密码保存到系统中")
    print("\n或者使用以下测试密码（如果WordPress允许）：")
    print(f"密码: {formatted_password}")
    print("\n" + "=" * 60)
    
    # 提供更新数据库的命令
    print("\n更新数据库命令：")
    print(f"""
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from app.services.wordpress_site_service import WordPressSiteService

async def update():
    async for db in get_db():
        service = WordPressSiteService(db)
        # 更新站点8（荣耀测试2）
        await service.update_site(8, api_password='{formatted_password}')
        print('✅ 密码已更新')
        break

asyncio.run(update())
"
    """)


if __name__ == "__main__":
    asyncio.run(generate_app_password())
