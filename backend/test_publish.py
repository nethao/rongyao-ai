#!/usr/bin/env python3
"""
测试WordPress发布功能
"""
import asyncio
import sys
from sqlalchemy import select, text
from app.database import get_db
from app.models.draft import Draft
from app.models.submission import Submission
from app.services.publish_service import PublishService


async def test_publish():
    """测试发布功能"""
    
    async for db in get_db():
        try:
            # 1. 查找最新的草稿
            result = await db.execute(
                select(Draft)
                .where(Draft.status == 'draft')
                .order_by(Draft.id.desc())
                .limit(1)
            )
            draft = result.scalar_one_or_none()
            
            if not draft:
                print("❌ 没有找到可用的草稿")
                return
            
            print(f"✅ 找到草稿 ID: {draft.id}")
            print(f"   版本: {draft.current_version}")
            print(f"   内容长度: {len(draft.current_content)} 字符")
            
            # 2. 获取关联的投稿（使用text查询避免lazy loading）
            result = await db.execute(
                text("""
                    SELECT s.email_subject, COUNT(si.id) as image_count
                    FROM submissions s
                    LEFT JOIN submission_images si ON si.submission_id = s.id
                    WHERE s.id = :submission_id
                    GROUP BY s.id, s.email_subject
                """),
                {"submission_id": draft.submission_id}
            )
            submission_info = result.fetchone()
            
            if submission_info:
                print(f"✅ 关联投稿: {submission_info.email_subject}")
                print(f"   图片数量: {submission_info.image_count}")
            
            # 3. 查找可用的WordPress站点
            result = await db.execute(
                text("SELECT id, name, url, active FROM wordpress_sites WHERE active = true LIMIT 1")
            )
            site = result.fetchone()
            
            if not site:
                print("❌ 没有找到激活的WordPress站点")
                return
            
            print(f"✅ 找到站点: {site.name} ({site.url})")
            
            # 4. 测试发布
            print("\n开始发布测试...")
            publish_service = PublishService(db)
            
            success, post_id, error_msg, site_name = await publish_service.publish_draft(
                draft_id=draft.id,
                site_id=site.id,
                status="publish"
            )
            
            if success:
                print(f"✅ 发布成功！")
                print(f"   站点: {site_name}")
                print(f"   WordPress文章ID: {post_id}")
                print(f"   访问地址: {site.url}/wp-admin/post.php?post={post_id}&action=edit")
            else:
                print(f"❌ 发布失败: {error_msg}")
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            break


if __name__ == "__main__":
    print("=" * 60)
    print("WordPress发布功能测试")
    print("=" * 60)
    asyncio.run(test_publish())
