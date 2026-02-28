#!/usr/bin/env python3
"""
模拟美篇邮件抓取测试
"""
import sys
sys.path.insert(0, '/app')

import asyncio
from app.services.imap_fetcher import EmailData
from app.tasks.email_tasks import process_email
from app.services.document_processor import DocumentProcessor
from app.services.oss_service import OSSService
from datetime import datetime

async def test_meipian():
    # 模拟美篇邮件数据
    email_data = EmailData(
        subject="投，荣，测试单位，测试美篇抓取",
        from_addr="test@example.com",
        date=datetime.now(),
        body="""
        美篇文章链接：
        https://www.meipian.cn/5jwb658d?share_depth=3&s_uid=100878222&share_to=group_singlemessage&first_share_to=group_singlemessage&first_share_uid=28859448
        
        请查看上述美篇文章。
        """,
        attachments=[]
    )
    
    print("开始测试美篇抓取...")
    print(f"邮件主题: {email_data.subject}")
    print(f"邮件正文: {email_data.body}")
    
    # 初始化服务
    doc_processor = DocumentProcessor()
    oss_service = OSSService()
    
    try:
        await process_email(email_data, doc_processor, oss_service)
        print("\n✅ 美篇抓取测试成功！")
    except Exception as e:
        print(f"\n❌ 美篇抓取测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_meipian())
