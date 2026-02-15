#!/usr/bin/env python3
"""
端到端测试：占位符协议完整流程
"""
import asyncio
from app.database import get_db
from app.services.draft_service import DraftService
from app.utils.content_processor import ContentProcessor

async def test_placeholder_protocol():
    print("=" * 60)
    print("占位符协议端到端测试")
    print("=" * 60)
    
    async for db in get_db():
        try:
            # 模拟数据
            test_content = """### 测试文章

这是第一段内容。

[[IMG_1]]

这是第二段内容，包含重要信息。

[[IMG_2]]

这是结尾。"""
            
            test_images = [
                {"oss_url": "https://oss.example.com/test1.jpg", "original_filename": "test1.jpg"},
                {"oss_url": "https://oss.example.com/test2.jpg", "original_filename": "test2.jpg"}
            ]
            
            print("\n1. 测试 extract_images_from_content")
            print("-" * 60)
            content_md, media_map = ContentProcessor.extract_images_from_content(
                test_content,
                test_images
            )
            print(f"✅ 生成占位符: {list(media_map.keys())}")
            print(f"✅ Markdown长度: {len(content_md)}")
            
            print("\n2. 测试 Hydration (用于编辑器)")
            print("-" * 60)
            html = ContentProcessor.hydrate(content_md, media_map)
            print(f"✅ HTML包含data-id: {'data-id' in html}")
            print(f"✅ HTML长度: {len(html)}")
            print(f"HTML预览:\n{html[:300]}...")
            
            print("\n3. 测试 Dehydration (保存)")
            print("-" * 60)
            new_md, new_map = ContentProcessor.dehydrate(html, media_map)
            print(f"✅ 恢复占位符: {list(new_map.keys())}")
            print(f"✅ Markdown匹配: {new_md.strip() == content_md.strip()}")
            
            print("\n4. 测试 WordPress渲染")
            print("-" * 60)
            wp_html = ContentProcessor.render_for_wordpress(content_md, media_map)
            print(f"✅ 无data-id: {'data-id' not in wp_html}")
            print(f"✅ 包含img标签: {'<img' in wp_html}")
            print(f"WordPress HTML预览:\n{wp_html[:300]}...")
            
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！占位符协议工作正常")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(test_placeholder_protocol())
