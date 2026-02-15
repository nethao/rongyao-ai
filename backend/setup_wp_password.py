#!/usr/bin/env python3
"""
为WordPress站点配置应用程序密码
"""
import asyncio
from sqlalchemy import text
from app.database import get_db
from app.services.wordpress_site_service import WordPressSiteService


async def setup_wp_password():
    """设置WordPress应用程序密码"""
    
    async for db in get_db():
        try:
            site_service = WordPressSiteService(db)
            
            # 获取所有站点
            result = await db.execute(
                text("SELECT id, name, url, api_username FROM wordpress_sites WHERE active = true")
            )
            sites = result.fetchall()
            
            print("=" * 60)
            print("WordPress站点应用程序密码配置")
            print("=" * 60)
            print("\n请为每个站点配置应用程序密码：")
            print("（在WordPress后台：用户 -> 个人资料 -> 应用程序密码）\n")
            
            for site in sites:
                print(f"\n站点: {site.name}")
                print(f"URL: {site.url}")
                print(f"用户名: {site.api_username}")
                
                # 提示：需要手动在WordPress后台生成应用程序密码
                print("\n步骤：")
                print(f"1. 访问 {site.url}/wp-admin/")
                print(f"2. 登录用户: {site.api_username}")
                print("3. 进入 用户 -> 个人资料")
                print("4. 滚动到底部 '应用程序密码' 部分")
                print("5. 输入名称（如：荣耀AI系统）并点击 '添加新应用程序密码'")
                print("6. 复制生成的密码（格式：xxxx xxxx xxxx xxxx xxxx xxxx）")
                
                password = input("\n请输入应用程序密码（或按Enter跳过）: ").strip()
                
                if password:
                    # 更新密码
                    await site_service.update_site(
                        site_id=site.id,
                        api_password=password
                    )
                    print(f"✅ 已保存站点 {site.name} 的密码")
                    
                    # 测试连接
                    print("测试连接...")
                    from app.models.wordpress_site import WordPressSite
                    from app.services.wordpress_service import WordPressService
                    
                    # 重新获取站点（包含加密的密码）
                    site_obj = await site_service.get_site(site.id)
                    decrypted_password = site_service.get_decrypted_password(site_obj)
                    
                    wp_service = WordPressService(site_obj, decrypted_password)
                    success, message = await wp_service.verify_connection()
                    
                    if success:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ 连接失败: {message}")
                else:
                    print("⏭️  跳过")
            
            print("\n" + "=" * 60)
            print("配置完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            break


if __name__ == "__main__":
    asyncio.run(setup_wp_password())
