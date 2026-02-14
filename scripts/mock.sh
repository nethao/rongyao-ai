#!/bin/bash
# 模拟邮件抓取快捷脚本
# 用法: ./scripts/mock.sh <公众号链接> [标题]

cd /home/nethao/rongyao-ai

if [ -z "$1" ]; then
    echo "用法: ./scripts/mock.sh <公众号链接> [标题]"
    echo "示例: ./scripts/mock.sh https://mp.weixin.qq.com/s/xxx '测试文章'"
    exit 1
fi

URL="$1"
TITLE="${2:-测试文章}"

echo "🚀 开始模拟抓取..."
sudo docker-compose exec -T backend python /app/mock_email.py "$URL" "$TITLE"

echo ""
echo "📊 查看结果:"
sudo docker-compose exec -T backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        result = await db.execute(text('SELECT id, email_subject, status, (SELECT COUNT(*) FROM drafts WHERE submission_id = submissions.id) as draft_count, (SELECT COUNT(*) FROM submission_images WHERE submission_id = submissions.id) as image_count FROM submissions ORDER BY id DESC LIMIT 1'))
        row = result.fetchone()
        if row:
            print(f'✅ 投稿ID: {row[0]}')
            print(f'📝 标题: {row[1]}')
            print(f'📊 状态: {row[2]}')
            print(f'📄 草稿数: {row[3]}')
            print(f'🖼️  图片数: {row[4]}')
        break

asyncio.run(check())
"
