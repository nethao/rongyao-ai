"""
初始化 A/B/C/D 四个 WordPress 站点（若不存在则创建）
用于本地或测试环境，URL 为 http://a.com .. http://d.com，API 用户名默认 admin。
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.wordpress_site import WordPressSite

# 四站点默认配置（可通过环境变量 WP_API_USERNAME 覆盖用户名）
DEFAULT_SITES = [
    {"name": "A站", "url": "http://a.com"},
    {"name": "B站", "url": "http://b.com"},
    {"name": "C站", "url": "http://c.com"},
    {"name": "D站", "url": "http://d.com"},
]
DEFAULT_API_USERNAME = os.environ.get("WP_API_USERNAME", "admin")


async def init_wp_sites():
    await init_db()
    async with AsyncSessionLocal() as session:
        for cfg in DEFAULT_SITES:
            result = await session.execute(
                select(WordPressSite).where(WordPressSite.url == cfg["url"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"已存在: {cfg['name']} ({cfg['url']})")
                continue
            site = WordPressSite(
                name=cfg["name"],
                url=cfg["url"],
                api_username=DEFAULT_API_USERNAME,
                api_password_encrypted=None,
                active=True,
            )
            session.add(site)
            print(f"已创建: {cfg['name']} ({cfg['url']}), 用户名: {DEFAULT_API_USERNAME}")
        await session.commit()
    print("WordPress 站点初始化完成。请在 e.com 系统配置中为各站点填写「应用程序密码」。")


if __name__ == "__main__":
    asyncio.run(init_wp_sites())
