"""
内容处理器 - 占位符协议核心逻辑
Placeholder Protocol: [[IMG_1]], [[IMG_2]], etc.
"""
import re
import markdown
from typing import Dict, Tuple
from bs4 import BeautifulSoup


class ContentProcessor:
    """
    内容处理器 - 实现占位符协议的核心转换逻辑
    """
    
    @staticmethod
    def _sanitize_html(raw_html: str) -> str:
        """
        Post-process HTML：仅移除完全空的段落（<p></p>、<p><br></p>），
        不再 unwrap <li> 内的 <p>，避免破坏列表与段落排版。
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        for p in list(soup.find_all('p')):
            if not p.get_text(strip=True) and not p.find('img'):
                if len(p.contents) == 0 or (len(p.contents) == 1 and p.find('br')):
                    p.decompose()
        return str(soup)

    @staticmethod
    def hydrate(md_text: str, media_map: Dict[str, str]) -> str:
        """
        Hydration: Markdown + 占位符 → HTML (用于Tiptap加载)
        
        Args:
            md_text: 带有[[IMG_x]]占位符的Markdown文本
            media_map: 占位符到OSS URL的映射 {"[[IMG_1]]": "https://oss..."}
            
        Returns:
            HTML字符串，img标签包含data-id属性
        """
        if not md_text:
            return ""
        media_map = media_map or {}
        
        # 0. 兼容旧格式：![图片N](URL) -> [[IMG_N]]
        md_text = re.sub(r'!\[图片(\d+)\]\(([^)]+)\)', lambda m: f'[[IMG_{m.group(1)}]]', md_text)
        
        # 1. 修复AI返回的格式问题：标题后没换行
        # ### 标题 内容 -> ### 标题\n\n内容
        md_text = re.sub(r'(#{2,4})\s+([^\n]+?)\s+([^#\n])', r'\1 \2\n\n\3', md_text)
        
        # 2. 清理Markdown中的多余空行
        md_text = re.sub(r'\n{3,}', '\n\n', md_text)
        
        # 3. 将Markdown转换为HTML
        html = markdown.markdown(
            md_text,
            extensions=['extra', 'sane_lists']
        )
        
        # 4. Sanitize
        html = ContentProcessor._sanitize_html(html)
        
        # 5. 替换占位符为img标签
        for placeholder, oss_url in media_map.items():
            img_tag = f'<img src="{oss_url}" data-id="{placeholder}" style="max-width:100%; height:auto;" alt="图片" />'
            html = html.replace(placeholder, img_tag)
        
        return html
    
    @staticmethod
    def dehydrate(html_str: str, old_media_map: Dict[str, str] = None) -> Tuple[str, Dict[str, str]]:
        """
        Dehydration: HTML → Markdown + 占位符 (用于保存)
        
        Args:
            html_str: 从Tiptap接收的HTML
            old_media_map: 旧的media_map（用于验证）
            
        Returns:
            (md_text, new_media_map)
        """
        if not html_str:
            return "", {}
        
        old_media_map = old_media_map or {}
        new_media_map = {}
        next_img_id = 1
        
        # 解析HTML
        soup = BeautifulSoup(html_str, 'html.parser')
        
        # 处理所有 img 标签
        for img in soup.find_all('img'):
            src = img.get('src', '')
            data_id = img.get('data-id', '')
            
            # 情况1: 有data-id，说明是旧图片
            if data_id and data_id.startswith('[[IMG_'):
                placeholder = data_id
                new_media_map[placeholder] = src
                img.replace_with(placeholder)
            # 情况2: 没有data-id，说明是新上传的图片
            elif src:
                while f'[[IMG_{next_img_id}]]' in new_media_map:
                    next_img_id += 1
                placeholder = f'[[IMG_{next_img_id}]]'
                new_media_map[placeholder] = src
                img.replace_with(placeholder)
                next_img_id += 1

        # 保留 video 标签：html2text 会丢失，先抽出并替换为占位符，转 markdown 后再插回（并统一加 controls）
        video_blocks = []
        for video in soup.find_all('video'):
            video_html = ContentProcessor._ensure_video_controls(str(video))
            video_blocks.append(video_html)
            video.replace_with(f'[[VIDEO_BLOCK_{len(video_blocks)}]]')
        
        # 转换 HTML 为 Markdown
        html_cleaned = str(soup)
        md_text = ContentProcessor._html_to_markdown(html_cleaned)
        for i, block in enumerate(video_blocks, 1):
            md_text = md_text.replace(f'[[VIDEO_BLOCK_{i}]]', '\n\n' + block + '\n\n')
        
        return md_text, new_media_map
    
    @staticmethod
    def _ensure_video_controls(html_or_tag: str) -> str:
        """
        确保所有 <video> 标签包含 controls 属性（编辑器展示与发布到 WP 均需要）。
        单标签输入时返回单个 <video>；完整 HTML 时返回 body 内片段（不包 <html><body>）。
        """
        if not html_or_tag or '<video' not in html_or_tag:
            return html_or_tag
        soup = BeautifulSoup(html_or_tag, 'html.parser')
        for v in soup.find_all('video'):
            if v.get('controls') is None:
                v['controls'] = ''
        videos = soup.find_all('video')
        # 单标签输入（仅一个 video，且为 body 唯一子节点）时只返回该标签
        if len(videos) == 1 and soup.find('body'):
            body = soup.find('body')
            if len(body.find_all(recursive=False)) == 1:
                return str(videos[0])
        # 完整 HTML：返回 body 内容，避免把 <html><body> 发给 WP
        if soup.find('body'):
            return soup.body.decode_contents()
        return str(soup)

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """
        简单的HTML到Markdown转换
        """
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.body_width = 0  # 不自动换行
        
        md = h.handle(html)
        
        # 清理多余空行
        md = re.sub(r'\n{3,}', '\n\n', md)
        
        return md.strip()
    
    @staticmethod
    def extract_images_from_content(content: str, images: list) -> Tuple[str, Dict[str, str]]:
        """
        从原始内容中提取图片并生成占位符
        用于Stage 1: Ingestion
        
        Args:
            content: 原始内容（可能包含Markdown图片语法）
            images: 图片列表 [{"oss_url": "...", "original_filename": "..."}, ...]
            
        Returns:
            (content_with_placeholders, media_map)
        """
        media_map = {}
        content_with_placeholders = content
        
        # 为每个图片生成占位符
        for idx, img in enumerate(images, start=1):
            placeholder = f'[[IMG_{idx}]]'
            media_map[placeholder] = img['oss_url']
            
            # 替换Markdown图片语法: ![图片N](url) → [[IMG_N]]
            pattern = rf'!\[图片{idx}\]\([^\)]+\)'
            content_with_placeholders = re.sub(pattern, placeholder, content_with_placeholders)
            
            # 替换其他可能的格式
            if img.get('original_filename'):
                pattern = rf'!\[([^\]]*)\]\({re.escape(img["original_filename"])}\)'
                content_with_placeholders = re.sub(pattern, placeholder, content_with_placeholders)
        
        return content_with_placeholders, media_map
    
    @staticmethod
    def render_for_wordpress(md_text: str, media_map: Dict[str, str]) -> str:
        """
        渲染用于WordPress发布
        Stage 5: Publishing
        
        Args:
            md_text: 带占位符的Markdown
            media_map: 占位符映射
            
        Returns:
            最终的HTML（标准img标签，无data-id）
        """
        # 转换Markdown为HTML
        html = markdown.markdown(
            md_text,
            extensions=['extra', 'nl2br', 'sane_lists']
        )
        
        # 替换占位符为标准 img 标签
        for placeholder, oss_url in (media_map or {}).items():
            img_tag = f'<img src="{oss_url}" style="max-width:100%; height:auto;" alt="图片" />'
            html = html.replace(placeholder, img_tag)

        # 确保发布到 WP 的 video 标签带 controls
        html = ContentProcessor._ensure_video_controls(html)
        
        return html
