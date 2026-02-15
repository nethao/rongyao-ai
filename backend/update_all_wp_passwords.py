#!/usr/bin/env python3
"""
批量更新WordPress站点密码
"""
import asyncio
from app.database import get_db
from app.services.wordpress_site_service import WordPressSiteService
from app.schemas.wordpress import WordPressSiteUpdate

# 在这里填入你的WordPress应用程序密码
# 格式：xxxx xxxx xxxx xxxx xxxx xxxx
PASSWORDS = {
    8: "你的密码",  # 荣耀测试2 (http://a.com)
    7: "你的密码",  # 争先测试 (http://b.com)
    9: "你的密码",  # 政企测试 (http://d.com)
    10: "你的密码", # 时代测试 (http://c.com)
}

async def update_passwords():
    async for db in get_db():
        service = WordPressSiteService(db)
        
        for site_id, password in PASSWORDS.items():
            if password == "你的密码":
                print(f"⏭️  跳过站点{site_id}（未配置密码）")
                continue
                
            await service.update_site(site_id, WordPressSiteUpdate(api_password=password))
            print(f"✅ 已更新站点{site_id}的密码")
            
            # 验证
            site = await service.get_site(site_id)
            decrypted = service.get_decrypted_password(site)
            print(f"   解密验证: {'✅' if decrypted == password else '❌'}")
        
        break

if __name__ == "__main__":
    print("=" * 60)
    print("批量更新WordPress应用程序密码")
    print("=" * 60)
    asyncio.run(update_passwords())
    print("\n完成！运行测试：python test_publish.py")
