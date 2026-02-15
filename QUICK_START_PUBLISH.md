# WordPress发布功能 - 快速开始

## 🚀 5分钟快速配置

### 步骤1：生成应用程序密码

访问WordPress后台：http://a.com/wp-admin/

1. 登录（admin/admin）
2. 用户 → 个人资料
3. 滚动到底部"应用程序密码"
4. 名称输入：`荣耀AI系统`
5. 点击"添加新应用程序密码"
6. **复制生成的密码**（格式：xxxx xxxx xxxx xxxx xxxx xxxx）

### 步骤2：更新系统配置

```bash
# 替换下面的 YOUR_PASSWORD 为你复制的密码
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from app.services.wordpress_site_service import WordPressSiteService

async def update():
    async for db in get_db():
        service = WordPressSiteService(db)
        await service.update_site(8, api_password='YOUR_PASSWORD')
        print('✅ 密码已更新')
        break

asyncio.run(update())
"
```

### 步骤3：测试发布

```bash
sudo docker-compose exec backend python test_publish.py
```

看到 `✅ 发布成功！` 就完成了！

## 🎯 前端使用

1. 访问 http://e.com
2. 登录（admin/admin123）
3. 点击投稿"查看草稿"
4. 编辑内容并保存
5. 点击"发布"按钮
6. 选择站点
7. 确认发布

## 📝 配置其他站点

重复步骤1-3，修改站点ID：

- 站点7 (http://b.com)：`update_site(7, ...)`
- 站点9 (http://d.com)：`update_site(9, ...)`
- 站点10 (http://c.com)：`update_site(10, ...)`

## ❓ 常见问题

**Q: 提示"401 Unauthorized"？**  
A: 应用程序密码未配置或错误，重新生成并更新。

**Q: 提示"站点未激活"？**  
A: 在数据库中激活站点或使用其他站点。

**Q: 图片显示不正常？**  
A: 图片已自动替换为OSS URL，检查OSS配置。

## 📞 需要帮助？

查看详细文档：`WORDPRESS_PUBLISH_COMPLETE.md`
