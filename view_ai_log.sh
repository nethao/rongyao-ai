#!/bin/bash
# AI改写详细日志查看器

echo "=========================================="
echo "AI改写任务详细日志"
echo "=========================================="
echo ""

# 获取最新的任务ID
TASK_ID=$(sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "Task transform_content" | tail -1 | grep -oP '\[[\w-]+\]' | tr -d '[]')

if [ -z "$TASK_ID" ]; then
    echo "❌ 未找到AI改写任务"
    exit 1
fi

echo "📋 任务ID: $TASK_ID"
echo ""

echo "=== 1. 任务基本信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "开始AI转换任务|submission_id"
echo ""

echo "=== 2. LLM配置信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "LLM Service|model|base_url"
echo ""

echo "=== 3. Prompt构建信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "构建提示词|source_name|reference_date|来源名称|参考日期"
echo ""

echo "=== 4. 内容处理信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "原文处理|总长度|占位符|图片"
echo ""

echo "=== 5. API调用信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "Calling LLM|HTTP Request|POST"
echo ""

echo "=== 6. 转换结果信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "transformation completed|Output length|Tokens|AI转换完成"
echo ""

echo "=== 7. 草稿保存信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "草稿|draft"
echo ""

echo "=== 8. 任务完成信息 ==="
sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "$TASK_ID" | grep -E "succeeded|failed|Task.*transform_content"
echo ""

echo "=========================================="
echo "详细统计"
echo "=========================================="

# 从数据库获取详细信息
sudo docker-compose exec -T backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        # 获取最新投稿
        result = await db.execute(text('SELECT id, email_subject, status FROM submissions ORDER BY id DESC LIMIT 1'))
        row = result.fetchone()
        if row:
            print(f'投稿ID: {row[0]}')
            print(f'标题: {row[1][:50]}...')
            print(f'状态: {row[2]}')
            
            # 获取草稿信息
            draft = await db.execute(text('SELECT id, current_version, LENGTH(original_content), LENGTH(current_content) FROM drafts WHERE submission_id = :sid'), {'sid': row[0]})
            d = draft.fetchone()
            if d:
                print(f'草稿ID: {d[0]}')
                print(f'当前版本: {d[1]}')
                print(f'原文长度: {d[2]} 字符')
                print(f'转换后长度: {d[3]} 字符')
                print(f'长度变化: {d[3] - d[2]:+d} 字符 ({(d[3]/d[2]-1)*100:+.1f}%)')
                
                # 获取版本历史
                versions = await db.execute(text('SELECT version, LENGTH(content), created_at FROM draft_versions WHERE draft_id = :did ORDER BY version DESC LIMIT 5'), {'did': d[0]})
                print(f'\n版本历史:')
                for v in versions:
                    print(f'  版本{v[0]}: {v[1]} 字符, {v[2]}')
        break

asyncio.run(check())
" 2>/dev/null

echo ""
echo "=========================================="
echo "Prompt模板（当前使用）"
echo "=========================================="
echo ""
echo "来源单位: 该单位（未识别）"
echo "参考日期: $(date '+%Y年%m月%d日')"
echo ""
echo "核心规则:"
echo "  1. 人称转换: 我→他/她, 我们→该单位"
echo "  2. 引用保护: 引号内容完整保留"
echo "  3. 图片占位符: [IMAGE_PLACEHOLDER_N] 必须保留"
echo "  4. 时间规范: 今天→具体日期"
echo "  5. 排版要求: 抛弃装饰性排版，仅保留正文和图片"
echo ""
