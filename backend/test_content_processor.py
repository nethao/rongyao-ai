#!/usr/bin/env python3
"""
测试ContentProcessor占位符协议
"""
from app.utils.content_processor import ContentProcessor

# 测试数据
md_text = """### 亲人的爱要见行动

[[IMG_1]]

亲人的付出，是发自心底的牵挂与担当。

[[IMG_2]]

真正的亲情，从来不是挂在嘴边的客套与承诺。"""

media_map = {
    "[[IMG_1]]": "https://oss.example.com/image1.jpg",
    "[[IMG_2]]": "https://oss.example.com/image2.jpg"
}

print("=" * 60)
print("测试 ContentProcessor")
print("=" * 60)

# 测试 Hydration
print("\n1. Hydration (MD → HTML)")
print("-" * 60)
html = ContentProcessor.hydrate(md_text, media_map)
print("输入 Markdown:")
print(md_text[:100] + "...")
print("\n输出 HTML:")
print(html[:300] + "...")

# 测试 Dehydration
print("\n2. Dehydration (HTML → MD)")
print("-" * 60)
md_result, map_result = ContentProcessor.dehydrate(html, media_map)
print("输入 HTML:")
print(html[:200] + "...")
print("\n输出 Markdown:")
print(md_result[:200] + "...")
print("\n输出 media_map:")
print(map_result)

# 测试 WordPress渲染
print("\n3. WordPress Rendering")
print("-" * 60)
wp_html = ContentProcessor.render_for_wordpress(md_text, media_map)
print("WordPress HTML:")
print(wp_html[:300] + "...")

# 验证占位符保留
print("\n4. 验证")
print("-" * 60)
print(f"✅ 占位符保留: {'[[IMG_1]]' in md_result and '[[IMG_2]]' in md_result}")
print(f"✅ media_map正确: {len(map_result) == 2}")
print(f"✅ HTML包含data-id: {'data-id' in html}")
print(f"✅ WordPress HTML无data-id: {'data-id' not in wp_html}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
