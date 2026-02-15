#!/bin/bash
echo "请提供其他3个站点的WordPress应用程序密码："
echo ""
echo "站点7 - 争先测试 (http://b.com)"
read -p "密码: " pass_b
echo ""
echo "站点9 - 政企测试 (http://d.com)"
read -p "密码: " pass_d
echo ""
echo "站点10 - 时代测试 (http://c.com)"
read -p "密码: " pass_c
echo ""
echo "正在更新..."

cd /home/nethao/rongyao-ai && sudo docker-compose exec -T backend python -c "
import asyncio
from app.database import get_db
from app.services.wordpress_site_service import WordPressSiteService
from app.schemas.wordpress import WordPressSiteUpdate

async def update():
    async for db in get_db():
        service = WordPressSiteService(db)
        
        if '$pass_b':
            await service.update_site(7, WordPressSiteUpdate(api_password='$pass_b'))
            print('✅ 已更新站点7 (争先测试)')
        
        if '$pass_d':
            await service.update_site(9, WordPressSiteUpdate(api_password='$pass_d'))
            print('✅ 已更新站点9 (政企测试)')
        
        if '$pass_c':
            await service.update_site(10, WordPressSiteUpdate(api_password='$pass_c'))
            print('✅ 已更新站点10 (时代测试)')
        
        break

asyncio.run(update())
"

echo ""
echo "✅ 密码更新完成！"
