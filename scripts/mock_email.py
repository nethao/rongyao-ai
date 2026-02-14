#!/usr/bin/env python3
"""
模拟邮件抓取脚本
用法: python scripts/mock_email.py <公众号链接>
"""
import sys
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/app')

from app.tasks.email_tasks import process_email
from app.services.document_processor import DocumentProcessor
from app.services.oss_service import OSSService
from app.config import settings


class MockEmail:
    """模拟邮件对象"""
    def __init__(self, url, title=None):
        # 默认标题
        if not title:
            title = "测试文章"
        
        self.subject = f'投，头，汉台区图书馆，{title}'
        self.body = url
        self.attachments = []
        self.from_addr = '372895768@qq.com'
        self.date = datetime.now()


async def mock_fetch(url, title=None):
    """模拟抓取邮件"""
    email = MockEmail(url, title)
    doc_processor = DocumentProcessor('/tmp/uploads')
    oss_service = OSSService(
        settings.OSS_ACCESS_KEY_ID,
        settings.OSS_ACCESS_KEY_SECRET,
        settings.OSS_ENDPOINT,
        settings.OSS_BUCKET_NAME
    )
    
    print(f'📧 开始处理邮件: {email.subject}')
    print(f'🔗 链接: {url}')
    
    await process_email(email, doc_processor, oss_service)
    
    print('✅ 邮件处理完成')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python scripts/mock_email.py <公众号链接> [标题]')
        print('示例: python scripts/mock_email.py https://mp.weixin.qq.com/s/xxx "测试文章"')
        sys.exit(1)
    
    url = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(mock_fetch(url, title))
