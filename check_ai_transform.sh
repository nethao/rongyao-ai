#!/bin/bash
# 检查AI改写任务状态

echo "=== 检查Celery Worker日志（最近50行）==="
sudo docker-compose logs --tail=50 celery_worker | grep -E "AI转换|transform|ERROR|WARNING"

echo ""
echo "=== 检查最新投稿和草稿状态 ==="
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        # 检查最新投稿
        result = await db.execute(text('SELECT id, email_subject, status FROM submissions ORDER BY id DESC LIMIT 1'))
        row = result.fetchone()
        if row:
            print(f'投稿ID: {row[0]}, 状态: {row[2]}')
            
            # 检查草稿
            draft = await db.execute(text('SELECT id, current_version, LENGTH(current_content) FROM drafts WHERE submission_id = :sid'), {'sid': row[0]})
            d = draft.fetchone()
            if d:
                print(f'草稿ID: {d[0]}, 版本: {d[1]}, 内容长度: {d[2]}')
                
                # 检查版本历史
                versions = await db.execute(text('SELECT version, created_at FROM draft_versions WHERE draft_id = :did ORDER BY version DESC LIMIT 3'), {'did': d[0]})
                print('最近版本:')
                for v in versions:
                    print(f'  版本{v[0]}: {v[1]}')
        break

asyncio.run(check())
"
