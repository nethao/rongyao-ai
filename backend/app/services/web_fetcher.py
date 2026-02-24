"""
网页抓取服务
抓取公众号和美篇文章内容
"""
import ipaddress
import re
import socket
from urllib.parse import urlparse
import requests
from typing import Optional, Tuple, List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

ALLOWED_URL_HOSTS = {
    "mp.weixin.qq.com",
    "www.meipian.cn",
    "meipian.cn",
}


def _validate_url(url: str) -> None:
    """SSRF 防护：仅允许白名单域名且禁止解析到内网 IP"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不允许的 URL 协议: {parsed.scheme}")
    host = parsed.hostname
    if not host:
        raise ValueError("URL 缺少主机名")
    if host not in ALLOWED_URL_HOSTS:
        raise ValueError(f"不允许抓取的域名: {host}")
    try:
        resolved = socket.getaddrinfo(host, None)
        for _, _, _, _, addr in resolved:
            ip = ipaddress.ip_address(addr[0])
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                raise ValueError(f"目标域名解析到内网地址: {ip}")
    except socket.gaierror:
        raise ValueError(f"域名解析失败: {host}")


class WebFetcher:
    """网页内容抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://mp.weixin.qq.com/',
        })
        self.session.max_redirects = 3
    
    def fetch_weixin_article(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
        """
        抓取微信公众号文章
        
        Args:
            url: 公众号文章链接
            
        Returns:
            (标题, Markdown内容, 原始HTML, 图片URL列表)
        """
        try:
            _validate_url(url)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title_tag = soup.find('h1', class_='rich_media_title')
            title = title_tag.get_text(strip=True) if title_tag else None
            
            # 提取正文
            content_tag = soup.find('div', class_='rich_media_content')
            if not content_tag:
                logger.error("未找到文章内容")
                return None, None, None, []
            
            # 移除隐藏样式，确保内容可见
            if content_tag.get('style'):
                style = content_tag.get('style', '')
                style = style.replace('visibility: hidden;', '').replace('opacity: 0;', '')
                content_tag['style'] = style
            
            # 将所有图片的data-src转换为src（用于HTML预览）
            for img in content_tag.find_all('img'):
                data_src = img.get('data-src')
                if data_src and not img.get('src'):
                    img['src'] = data_src
            
            # 保存原始HTML（保留所有样式）
            original_html = str(content_tag)
            
            # 提取图片URL并在原位置插入占位符（用于Markdown）
            images = []
            img_index = 0
            content_copy = BeautifulSoup(str(content_tag), 'html.parser')
            for img in content_copy.find_all('img'):
                img_url = img.get('data-src') or img.get('src')
                if img_url:
                    images.append(img_url)
                    # 用占位符替换img标签，保留图片位置
                    img.replace_with(f'\n[IMAGE_{img_index}]\n')
                    img_index += 1
            
            # 提取Markdown内容（包含图片占位符）
            markdown_content = content_copy.get_text(separator='\n', strip=True)
            
            # 将占位符替换为Markdown图片语法
            for i, img_url in enumerate(images):
                markdown_content = markdown_content.replace(f'[IMAGE_{i}]', f'\n![图片{i+1}]({img_url})\n')
            
            logger.info(f"成功抓取公众号文章: {title}, 图片数: {len(images)}")
            return title, markdown_content, original_html, images
            
        except Exception as e:
            logger.error(f"抓取公众号文章失败: {e}")
            return None, None, None, []
    
    async def fetch_meipian_article_async(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """
        抓取美篇文章（使用Playwright异步API渲染JavaScript）
        
        Args:
            url: 美篇文章链接
            
        Returns:
            (标题, 内容文本, 图片URL列表, 原始HTML)
        """
        try:
            _validate_url(url)
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 访问页面并等待加载
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待图片加载
                await page.wait_for_timeout(2000)
                
                # 获取渲染后的HTML
                html_content = await page.content()
                await browser.close()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题（从caption-title-html）
            title = None
            title_tag = soup.find('div', {'class': 'caption-title-html'})
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # 提取正文（使用mp-article-tpl容器）
            content_tag = soup.find('div', {'class': 'mp-article-tpl'})
            
            if not content_tag:
                logger.error("未找到mp-article-tpl容器")
                return title, None, [], None
            
            # 移除标题（避免正文重复）
            title_in_content = content_tag.find('div', {'class': 'caption-title-html'})
            if title_in_content:
                title_in_content.decompose()
            
            # 移除副标题
            subhead = content_tag.find('div', {'class': 'mp-article-caption-subhead'})
            if subhead:
                subhead.decompose()
            
            # 移除script、style等
            for unwanted in content_tag(['script', 'style', 'header', 'footer', 'nav']):
                unwanted.decompose()
            
            # 提取图片URL
            images = []
            img_attrs = ['data-src', 'src', 'data-original', 'data-lazy-src']
            
            for img in content_tag.find_all('img'):
                img_url = None
                for attr in img_attrs:
                    img_url = img.get(attr)
                    if img_url:
                        break
                
                if img_url and not img_url.startswith('data:'):
                    if any(x in img_url.lower() for x in ['icon', 'avatar', 'badge', 'member', 'gift', 'logo', 'qrcode', 'code-logo']):
                        continue
                    
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://www.meipian.cn' + img_url
                    elif not img_url.startswith('http'):
                        img_url = 'https://www.meipian.cn/' + img_url
                    
                    if img_url not in images:
                        images.append(img_url)
            
            # 提取纯文本内容（用于Markdown）
            content_text = content_tag.get_text(separator='\n', strip=True)
            
            # 保存HTML（保持图文排版）
            original_html = str(content_tag)
            
            logger.info(f"成功抓取美篇文章: {title}, 内容长度: {len(content_text)}, 图片数: {len(images)}")
            return title, content_text, images, original_html
            
        except Exception as e:
            logger.error(f"抓取美篇文章失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None, [], None
    
    def fetch_meipian_article(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """
        抓取美篇文章（同步包装器）
        """
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.fetch_meipian_article_async(url))
    
    def download_image(self, url: str) -> Optional[bytes]:
        """
        下载图片
        
        Args:
            url: 图片URL
            
        Returns:
            图片二进制数据
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"下载图片失败 {url}: {e}")
            return None
