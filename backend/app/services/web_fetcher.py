"""
网页抓取服务
抓取公众号和美篇文章内容
"""
import html as html_module
import ipaddress
import re
import socket
from urllib.parse import urlparse, urljoin
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

# 通用URL抓取不受白名单限制（由调用方控制）
GENERIC_URL_ENABLED = True


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


# 中文文章平台噪音行过滤（简篇/美篇/微信等平台通用）
_ARTICLE_NOISE_RE = re.compile(
    r'^(删除|阅读\s*\d+|收藏(TA)?|投诉|需扫码.*|文章后点击.*|该内容使用了AI.*|'
    r'文章由.+编辑制作|.*工作版$|赞\s*\d*|评论\s*\d*|转发\s*\d*|分享|举报|'
    r'扫码在手机上打开|点击更新提醒|创建于.+|发布于.+)$'
)

# 按优先级排列的文章容器 CSS 类名（含简篇/美篇/常见新闻站）
_ARTICLE_CONTAINER_CLASSES = [
    'mp-article',          # 简篇 jianpian.cn
    'rich_media_content',  # 微信公众号
    'article-content',
    'article-body',
    'article__body',
    'article__content',
    'post-content',
    'post-body',
    'entry-content',
    'content-article',
    'news-content',
    'detail-content',
    'main-content',
]


def _bs4_article_extract(html: str, url: str):
    """
    BS4 容器提取：当 trafilatura 抓取不足时用于补充。
    返回 (title, text, article_html) 或 (title, None, None)。
    - text: Markdown 格式（段落间双换行）
    - article_html: 仅含文章容器的干净 HTML（用于 iframe 预览）
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 提取标题
    title = None
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
    elif soup.title:
        title = soup.title.string

    # 删除干扰标签
    for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                     'button', 'iframe', 'noscript']):
        tag.decompose()

    # 按优先级查找文章容器
    container = None
    for cls in _ARTICLE_CONTAINER_CLASSES:
        container = soup.find(attrs={'class': cls})
        if container:
            break
    if not container:
        container = soup.find('article') or soup.find('main')
    if not container:
        return title, None, None

    # 提取文本行并过滤噪音
    lines = []
    for line in container.get_text(separator='\n').splitlines():
        line = line.strip()
        if not line or len(line) < 5:
            continue
        if _ARTICLE_NOISE_RE.match(line):
            continue
        lines.append(line)

    # 去除相邻重复行
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    if not deduped or len('\n'.join(deduped).strip()) < 100:
        return title, None, None

    # 段落间用双换行（Markdown 格式）
    text = '\n\n'.join(deduped)

    # 构建干净的文章预览 HTML（供 iframe 显示）
    title_html = f'<h1 style="font-size:1.4em;margin-bottom:16px;">{title}</h1>' if title else ''
    paras = ''.join(f'<p style="margin:0 0 1em;line-height:1.8;">{p}</p>' for p in deduped)
    article_html = (
        '<html><head><meta charset="utf-8">'
        '<style>body{font-family:sans-serif;padding:20px;max-width:800px;margin:0 auto;color:#333;}'
        'p{margin:0 0 1em;line-height:1.8;}</style></head>'
        f'<body>{title_html}{paras}</body></html>'
    )

    return title, text, article_html


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
    
    def _fetch_meipian_with_requests(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """
        美篇 requests 方案：解析首屏 HTML 中的 SEO 用 <article> 块，无需浏览器。
        美篇在服务端会输出隐藏的 article（含标题和正文），适合无 Playwright 的 Docker 环境。
        """
        try:
            _validate_url(url)
        except ValueError:
            return None, None, [], None
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            resp.encoding = "utf-8"
        except Exception as e:
            logger.warning(f"美篇 requests 请求失败: {e}")
            return None, None, [], None

        soup = BeautifulSoup(resp.text, "html.parser")
        article = soup.find("article")
        if not article:
            return None, None, [], None

        title = None
        h1 = article.find("h1")
        if h1:
            a = h1.find("a")
            title = (a.get_text(strip=True) if a else h1.get_text(strip=True)) or None
        if not title and soup.find("title"):
            title = soup.find("title").get_text(strip=True)

        section = article.find("section")
        if not section:
            return title, None, [], None

        try:
            inner = section.decode_contents()
        except Exception:
            inner = str(section)
        unescaped = html_module.unescape(inner)
        content_soup = BeautifulSoup(unescaped, "html.parser")
        for tag in content_soup(["script", "style"]):
            tag.decompose()
        content_text = content_soup.get_text(separator="\n", strip=True)
        if not content_text or len(content_text.strip()) < 50:
            return title, None, [], None

        images = []
        for img in content_soup.find_all("img"):
            src = img.get("data-src") or img.get("src") or img.get("data-original")
            if not src or src.startswith("data:"):
                continue
            if any(x in src.lower() for x in ["icon", "avatar", "logo", "qrcode"]):
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin("https://www.meipian.cn", src)
            elif not src.startswith("http"):
                src = urljoin("https://www.meipian.cn/", src)
            if src not in images:
                images.append(src)

        original_html = f"<article><h1>{title or ''}</h1><section>{unescaped}</section></article>"
        logger.info(f"成功抓取美篇文章(requests): {title}, 内容长度: {len(content_text)}, 图片数: {len(images)}")
        return title, content_text, images, original_html

    async def _fetch_meipian_playwright_only(self, url: str) -> Optional[Tuple[Optional[str], Optional[str], List[str], Optional[str]]]:
        """仅用 Playwright 抓取美篇（用于 requests 有正文无图时补图）。失败返回 None。"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright 未安装")
            return None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2500)
                html_content = await page.content()
                await browser.close()
        except Exception as e:
            logger.warning(f"Playwright 启动或访问失败: {e}")
            return None

        soup = BeautifulSoup(html_content, "html.parser")
        title = None
        title_tag = soup.find("div", {"class": "caption-title-html"})
        if title_tag:
            title = title_tag.get_text(strip=True)
        content_tag = soup.find("div", {"class": "mp-article-tpl"})
        if not content_tag:
            logger.warning(f"Playwright 未找到 mp-article-tpl 容器")
            return None
        if content_tag.find("div", {"class": "caption-title-html"}):
            content_tag.find("div", {"class": "caption-title-html"}).decompose()
        subhead = content_tag.find("div", {"class": "mp-article-caption-subhead"})
        if subhead:
            subhead.decompose()
        for unwanted in content_tag(["script", "style", "header", "footer", "nav"]):
            unwanted.decompose()
        images = []
        for img in content_tag.find_all("img"):
            img_url = img.get("data-src") or img.get("src") or img.get("data-original") or img.get("data-lazy-src")
            if img_url and not img_url.startswith("data:"):
                if any(x in img_url.lower() for x in ["icon", "avatar", "badge", "member", "gift", "logo", "qrcode", "code-logo"]):
                    continue
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = "https://www.meipian.cn" + img_url
                elif not img_url.startswith("http"):
                    img_url = "https://www.meipian.cn/" + img_url
                if img_url not in images:
                    images.append(img_url)
        logger.info(f"Playwright 提取到 {len(images)} 张图片")
        content_text = content_tag.get_text(separator="\n", strip=True)
        original_html = str(content_tag)
        return (title, content_text, images, original_html)

    async def fetch_meipian_article_async(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """
        抓取美篇文章（优先 requests 解析 SEO 块，无需浏览器；失败再 Crawl4AI/Playwright）
        
        Args:
            url: 美篇文章链接
            
        Returns:
            (标题, 内容文本, 图片URL列表, 原始HTML)
        """
        try:
            _validate_url(url)
        except ValueError as e:
            logger.error(f"美篇 URL 校验失败: {e}")
            return None, None, [], None

        # 1）优先 requests：美篇首屏 HTML 含 SEO 用 article，无浏览器依赖
        import asyncio
        result = await asyncio.to_thread(self._fetch_meipian_with_requests, url)
        if result[0] is not None and result[1]:
            title_req, text_req, images_req, html_req = result
            # 有正文但无图时，尝试 Playwright 补抓图片（正文图由 JS 渲染，仅首屏 SEO 无图）
            if not images_req:
                logger.info(f"美篇 requests 无图，尝试 Playwright 补抓...")
                try:
                    pw_result = await self._fetch_meipian_playwright_only(url)
                    logger.info(f"Playwright 返回结果: {pw_result is not None}, 图片数: {len(pw_result[2]) if pw_result else 0}")
                    if pw_result and pw_result[2]:
                        logger.info(f"美篇 Playwright 补抓图片数: {len(pw_result[2])}")
                        return (title_req or pw_result[0], text_req or pw_result[1], pw_result[2], pw_result[3] or html_req)
                    else:
                        logger.warning(f"美篇 Playwright 补抓失败：未获取到图片")
                except Exception as e:
                    logger.warning(f"美篇 Playwright 补图失败: {e}", exc_info=True)
            return result

        # 2）Crawl4AI（需 Playwright 浏览器）
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            from urllib.parse import urljoin

            browser_config = BrowserConfig(headless=True, verbose=False)
            run_config = CrawlerRunConfig(
                word_count_threshold=50,
                cache_mode="bypass",
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url, config=run_config)
                if not result:
                    logger.error("Crawl4AI 返回空结果")
                    return None, None, [], None

                title = (result.metadata.get("title") or "").strip() or None
                text = result.markdown.fit_markdown or result.markdown.raw_markdown or ""

                images = []
                media = result.media or {}
                for img in media.get("images", []):
                    img_url = img.get("src") if isinstance(img, dict) else (img if isinstance(img, str) else None)
                    if not img_url or img_url.startswith("data:"):
                        continue
                    if any(x in img_url.lower() for x in ["icon", "avatar", "badge", "member", "gift", "logo", "qrcode", "code-logo"]):
                        continue
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    elif img_url.startswith("/"):
                        img_url = urljoin("https://www.meipian.cn", img_url)
                    elif not img_url.startswith("http"):
                        img_url = urljoin("https://www.meipian.cn/", img_url)
                    if img_url not in images:
                        images.append(img_url)

                logger.info(f"成功抓取美篇文章(Crawl4AI): {title}, 内容长度: {len(text)}, 图片数: {len(images)}")
                return title, text, images, result.html

        except ImportError:
            logger.warning("Crawl4AI 未安装，尝试 Playwright")
        except Exception as e:
            logger.warning(f"Crawl4AI 抓取美篇失败: {e}，尝试 Playwright")

        # 兜底：Playwright（本地或已正确安装 Chromium 的环境）
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                html_content = await page.content()
                await browser.close()

            soup = BeautifulSoup(html_content, "html.parser")
            title = None
            title_tag = soup.find("div", {"class": "caption-title-html"})
            if title_tag:
                title = title_tag.get_text(strip=True)
            content_tag = soup.find("div", {"class": "mp-article-tpl"})
            if not content_tag:
                logger.error("未找到 mp-article-tpl 容器")
                return title, None, [], None
            if content_tag.find("div", {"class": "caption-title-html"}):
                content_tag.find("div", {"class": "caption-title-html"}).decompose()
            subhead = content_tag.find("div", {"class": "mp-article-caption-subhead"})
            if subhead:
                subhead.decompose()
            for unwanted in content_tag(["script", "style", "header", "footer", "nav"]):
                unwanted.decompose()
            images = []
            for img in content_tag.find_all("img"):
                img_url = img.get("data-src") or img.get("src") or img.get("data-original") or img.get("data-lazy-src")
                if img_url and not img_url.startswith("data:"):
                    if any(x in img_url.lower() for x in ["icon", "avatar", "badge", "member", "gift", "logo", "qrcode", "code-logo"]):
                        continue
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    elif img_url.startswith("/"):
                        img_url = "https://www.meipian.cn" + img_url
                    elif not img_url.startswith("http"):
                        img_url = "https://www.meipian.cn/" + img_url
                    if img_url not in images:
                        images.append(img_url)
            content_text = content_tag.get_text(separator="\n", strip=True)
            original_html = str(content_tag)
            logger.info(f"成功抓取美篇文章(Playwright): {title}, 内容长度: {len(content_text)}, 图片数: {len(images)}")
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
    
    async def fetch_generic_url_async(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """
        抓取通用URL（非公众号、非美篇）
        优先用 trafilatura 提取正文，失败时降级到 Crawl4AI / Playwright

        Args:
            url: 网页链接

        Returns:
            (标题, 内容文本, 图片URL列表, 原始HTML)
        """
        import asyncio
        from urllib.parse import urljoin as _urljoin

        # ── 策略1：requests + trafilatura（最快，无需浏览器，专为新闻正文提取设计）──
        try:
            import trafilatura

            def _try_trafilatura():
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    return None, None, [], None

                text = trafilatura.extract(
                    downloaded,
                    include_tables=False,
                    include_comments=False,
                    favor_precision=True,
                    output_format='txt',
                    url=url,
                )

                metadata = trafilatura.extract_metadata(downloaded, default_url=url)
                title = metadata.title if metadata else None

                # trafilatura 内容不足时，用 BS4 容器提取补充
                bs4_html_override = None
                if not text or len(text.strip()) < 400:
                    bs4_title, bs4_text, bs4_html = _bs4_article_extract(downloaded, url)
                    if bs4_text and len(bs4_text.strip()) > len(text or ''):
                        logger.info(
                            f"trafilatura内容过短({len(text or '')}字)，"
                            f"BS4容器补充提取({len(bs4_text)}字)"
                        )
                        title = bs4_title or title
                        text = bs4_text
                        bs4_html_override = bs4_html  # 用干净的文章 HTML 替代整页 HTML

                if not text or len(text.strip()) < 100:
                    return None, None, [], None

                # 从 HTML 提取文章图片（去掉 logo/icon/二维码/GIF占位图 等干扰项）
                soup = BeautifulSoup(downloaded, 'html.parser')
                for junk in soup(['script', 'style', 'nav', 'header', 'footer']):
                    junk.decompose()
                images = []

                def _normalize_img_src(src):
                    """规范化图片URL：去CDN变换后缀、补全协议/路径"""
                    if not src or src.startswith('data:'):
                        return None
                    # 去掉字节跳动/VolcEngine等CDN图片变换后缀 (~tplv-...)
                    src = re.sub(r'~tplv-[^\s"\')]+', '', src)
                    # 去掉其他常见CDN变换参数 (@2x, !w600, _200x200 等)
                    src = re.sub(r'[@!_][0-9]+[xwh][^\s"\')]*$', '', src)
                    # 跳过 GIF（通常是懒加载占位图）
                    if src.lower().endswith('.gif') or '.gif?' in src.lower():
                        return None
                    if any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'banner', 'qrcode', 'wechat', '/user/']):
                        return None
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = _urljoin(url, src)
                    elif not src.startswith('http'):
                        src = _urljoin(url, src)
                    return src

                # 1) <img src/data-src/data-original>
                for img in soup.find_all('img'):
                    raw = img.get('src') or img.get('data-src') or img.get('data-original')
                    src = _normalize_img_src(raw)
                    if src and src not in images:
                        images.append(src)

                # 2) CSS background-image（jianpian/meipian等平台常用此方式存图片）
                for el in soup.find_all(style=True):
                    style_val = el.get('style', '')
                    for m_bg in re.finditer(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style_val):
                        src = _normalize_img_src(m_bg.group(1))
                        if src and src not in images:
                            images.append(src)

                # 如果 BS4 提供了干净的文章 HTML，用它替代整页 HTML
                final_html = bs4_html_override if bs4_html_override else downloaded
                return title, text, images, final_html

            title, text, images, html = await asyncio.to_thread(_try_trafilatura)
            if text and len(text.strip()) > 100:
                logger.info(f"trafilatura抓取成功: {title}, 内容长度: {len(text)}, 图片数: {len(images)}")
                return title, text, images, html

        except ImportError:
            logger.debug("trafilatura未安装，跳过")
        except Exception as e:
            logger.warning(f"trafilatura抓取失败: {e}")

        # ── 策略2：Crawl4AI（需 Playwright 浏览器，适合 JS 渲染页面）──
        logger.info(f"trafilatura未能提取，降级到Crawl4AI: {url}")
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            from urllib.parse import urljoin

            browser_config = BrowserConfig(headless=True, verbose=False)
            run_config = CrawlerRunConfig(word_count_threshold=50, cache_mode="bypass")

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url, config=run_config)

                title = result.metadata.get('title', '') or result.url
                text = result.markdown.fit_markdown or result.markdown.raw_markdown

                images = []
                if result.media and 'images' in result.media:
                    for img in result.media['images']:
                        if isinstance(img, dict) and 'src' in img:
                            img_url = img['src']
                        elif isinstance(img, str):
                            img_url = img
                        else:
                            continue
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = urljoin(url, img_url)
                        if img_url not in images:
                            images.append(img_url)

                logger.info(f"Crawl4AI抓取成功: {title}, 图片数: {len(images)}")
                return title, text, images, result.html

        except ImportError:
            logger.warning("Crawl4AI未安装，使用基础抓取方案")
            return await self._fetch_generic_fallback_async(url)
        except Exception as e:
            logger.error(f"Crawl4AI抓取失败: {e}，使用基础方案")
            return await self._fetch_generic_fallback_async(url)
    
    async def _fetch_generic_fallback_async(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """基础抓取方案（兜底）"""
        logger.info(f"使用基础方案抓取: {url}")
        
        try:
            from playwright.async_api import async_playwright
            from urllib.parse import urljoin
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)
                
                title = await page.title()
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                for unwanted in soup(['script', 'style', 'header', 'footer', 'nav']):
                    unwanted.decompose()
                
                text = soup.get_text(separator='\n', strip=True)
                
                images = []
                for img in soup.find_all('img'):
                    src = img.get('src') or img.get('data-src')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = urljoin(url, src)
                        images.append(src)
                
                await browser.close()
                
                logger.info(f"基础方案抓取成功: {title}")
                return title, text, images, content
                
        except Exception as e:
            logger.error(f"基础方案抓取失败: {e}")
            return None, None, [], None
    
    def fetch_generic_url(self, url: str) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """
        抓取通用URL（同步包装器）
        """
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.fetch_generic_url_async(url))
