#!/bin/bash
# AI改写详细报告

echo "=========================================="
echo "AI改写任务详细报告"
echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

echo "【任务执行流程】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /home/nethao/rongyao-ai && sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep -E "开始AI转换任务|LLM Service|构建提示词|原文处理|Calling LLM|HTTP Request|AI转换完成|草稿|succeeded" | tail -20
echo ""

echo "【使用的Prompt模板】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat << 'EOF'
你是一个专业的内容编辑助手。你的任务是将第一人称叙述转换为第三人称叙述。

**参考信息：**
- 来源单位：该单位（未识别到具体单位名）
- 参考日期：2026年02月14日

**核心转换规则：**

1. 人称转换
   - 我 → 他/她
   - 我们 → 该单位
   - 我局/我司 → 该单位

2. 引用内容保护
   - 引号内容完整保留

3. 图片占位符保护（重要）
   - [IMAGE_PLACEHOLDER_N] 必须完整保留
   - 不删除、不修改、不移动位置

4. 时间表述规范化
   - 今天 → 具体日期
   - 昨天/明天 → 计算具体日期

5. 排版要求（WordPress适配）
   - 抛弃装饰性排版
   - 仅保留正文和图片
   - 使用简洁扁平结构

**输出要求：**
- 直接返回转换后文本
- 不添加解释说明
- 纯净的可发布内容
EOF
echo ""

echo "【LLM配置】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "模型: qwen-turbo"
echo "API: https://dashscope.aliyuncs.com/compatible-mode/v1"
echo "Temperature: 0.7"
echo ""

echo "【处理统计】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /home/nethao/rongyao-ai && sudo docker-compose logs --tail=500 celery_worker 2>/dev/null | grep "原文处理\|AI转换完成\|Tokens\|succeeded" | tail -5
echo ""

echo "【数据库状态】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /home/nethao/rongyao-ai && sudo docker-compose exec -T backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        result = await db.execute(text('SELECT id, email_subject FROM submissions ORDER BY id DESC LIMIT 1'))
        row = result.fetchone()
        if row:
            print(f'投稿ID: {row[0]}')
            print(f'标题: {row[1][:50]}')
            
            draft = await db.execute(text('SELECT id, current_version, LENGTH(current_content) FROM drafts WHERE submission_id = :sid'), {'sid': row[0]})
            d = draft.fetchone()
            if d:
                print(f'草稿ID: {d[0]}')
                print(f'当前版本: {d[1]}')
                print(f'内容长度: {d[2]} 字符')
                
                versions = await db.execute(text('SELECT version, created_at FROM draft_versions WHERE draft_id = :did ORDER BY version DESC LIMIT 3'), {'did': d[0]})
                print(f'版本历史:')
                for v in versions:
                    print(f'  版本{v[0]}: {v[1]}')
        break

asyncio.run(check())
" 2>/dev/null

echo ""
echo "=========================================="
