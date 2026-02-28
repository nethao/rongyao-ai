"""
将四个 WordPress 站点的应用程序密码写入数据库（加密保存）。
用法: 传入 4 个密码，按顺序对应 A站(1)、B站(2)、C站(3)、D站(4)。
  python3 scripts/set_wp_passwords.py "pass_a" "pass_b" "pass_c" "pass_d"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.wordpress_site import WordPressSite
from app.utils.encryption import encrypt_value


async def main():
    if len(sys.argv) < 5:
        print("用法: python3 scripts/set_wp_passwords.py <A站密码> <B站密码> <C站密码> <D站密码>")
        sys.exit(1)
    passwords = [sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]]
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WordPressSite).order_by(WordPressSite.id).limit(4)
        )
        sites = list(result.scalars().all())
        if len(sites) < 4:
            print(f"只有 {len(sites)} 个站点，需要 4 个 (A/B/C/D)")
            sys.exit(1)
        for i, site in enumerate(sites):
            if i >= len(passwords):
                break
            site.api_password_encrypted = encrypt_value(passwords[i])
            print(f"已保存: {site.name} ({site.url})")
        await session.commit()
    print("完成。")


if __name__ == "__main__":
    asyncio.run(main())
