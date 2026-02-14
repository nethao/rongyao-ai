#!/usr/bin/env python3
"""
模拟邮件抓取脚本
"""
import sys
import asyncio
import argparse
from datetime import datetime

sys.path.insert(0, '/app')

from app.tasks.email_tasks import process_email
from app.services.document_processor import DocumentProcessor
from app.services.oss_service import OSSService
from app.config import settings


class MockEmail:
    def __init__(self, sender, subject, url):
        self.subject = subject
        self.body = url
        self.attachments = []
        self.from_addr = sender
        self.date = datetime.now()


async def mock_fetch(sender, subject, url):
    email = MockEmail(sender, subject, url)
    doc_processor = DocumentProcessor('/tmp/uploads')
    oss_service = OSSService(
        settings.OSS_ACCESS_KEY_ID,
        settings.OSS_ACCESS_KEY_SECRET,
        settings.OSS_ENDPOINT,
        settings.OSS_BUCKET_NAME
    )
    
    print(f'📧 处理: {subject}, {sender}')
    await process_email(email, doc_processor, oss_service)
    print('✅ 完成')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='模拟邮件抓取')
    parser.add_argument('--sender', required=True, help='发件人')
    parser.add_argument('--subject', required=True, help='邮件主题')
    parser.add_argument('--url', required=True, help='文章链接')
    
    args = parser.parse_args()
    asyncio.run(mock_fetch(args.sender, args.subject, args.url))
