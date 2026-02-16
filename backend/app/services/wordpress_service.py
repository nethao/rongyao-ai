"""
WordPress REST API客户端服务
"""
import httpx
import secrets
import string
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from app.models.wordpress_site import WordPressSite
import logging

logger = logging.getLogger(__name__)


class WordPressService:
    """WordPress REST API客户端"""
    
    # URL映射：外部域名 -> 容器名
    URL_MAPPING = {
        'http://a.com': 'http://wp_a',
        'http://b.com': 'http://wp_b',
        'http://c.com': 'http://wp_c',
        'http://d.com': 'http://wp_d',
    }

    def __init__(self, site: WordPressSite, api_password: str):
        """
        初始化WordPress服务
        
        Args:
            site: WordPress站点对象
            api_password: 解密后的API密码
        """
        self.site = site
        # 使用容器内部URL
        external_url = site.url.rstrip('/')
        self.base_url = self.URL_MAPPING.get(external_url, external_url)
        # 使用查询参数方式访问REST API（兼容未启用固定链接的WordPress）
        self.api_url = f"{self.base_url}/?rest_route=/wp/v2"
        self.username = site.api_username
        # 移除应用程序密码中的空格
        self.password = api_password.replace(' ', '') if api_password else api_password

    async def verify_connection(self) -> tuple[bool, Optional[str]]:
        """
        验证WordPress站点连接
        
        Returns:
            (是否成功, 错误信息)
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 尝试访问WordPress REST API根端点
                response = await client.get(
                    f"{self.base_url}/?rest_route=/",
                    auth=(self.username, self.password) if self.username else None
                )
                
                if response.status_code == 200:
                    data = response.json()
                    site_name = data.get('name', '未知站点')
                    return True, f"连接成功！站点: {site_name}"
                else:
                    return False, f"HTTP {response.status_code}: {response.text[:200]}"
                    
        except httpx.TimeoutException:
            return False, "连接超时"
        except httpx.ConnectError:
            return False, "无法连接到站点"
        except Exception as e:
            return False, f"连接错误: {str(e)}"

    async def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        categories: Optional[list[int]] = None,
        tags: Optional[list[int]] = None,
        author_id: Optional[int] = None
    ) -> tuple[bool, Optional[int], Optional[str]]:
        """
        创建WordPress文章
        
        Args:
            title: 文章标题
            content: 文章内容（HTML格式）
            status: 文章状态 ('draft', 'publish', 'pending')
            categories: 分类ID列表
            tags: 标签ID列表
            author_id: 作者ID（WordPress用户ID）
            
        Returns:
            (是否成功, 文章ID, 错误信息)
        """
        try:
            post_data: Dict[str, Any] = {
                "title": title,
                "content": content,
                "status": status
            }
            
            if categories:
                post_data["categories"] = categories
            if tags:
                post_data["tags"] = tags
            if author_id:
                post_data["author"] = author_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/posts",
                    json=post_data,
                    auth=(self.username, self.password)
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    post_id = result.get("id")
                    return True, post_id, None
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    return False, None, error_msg
                    
        except httpx.TimeoutException:
            return False, None, "发布超时"
        except httpx.ConnectError:
            return False, None, "无法连接到站点"
        except Exception as e:
            return False, None, f"发布错误: {str(e)}"

    async def get_user_by_username(self, username: str) -> Optional[int]:
        """
        根据用户名查询WordPress用户ID
        
        Args:
            username: 用户名
            
        Returns:
            用户ID，未找到返回None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/users",
                    params={"search": username},
                    auth=(self.username, self.password)
                )
                
                if response.status_code == 200:
                    users = response.json()
                    # 精确匹配用户名
                    for user in users:
                        if user.get("slug") == username or user.get("name") == username:
                            return user.get("id")
                    return None
                else:
                    logger.warning(f"查询WordPress用户失败: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"查询WordPress用户异常: {e}")
            return None

    async def create_user(self, username: str, email: str) -> Optional[int]:
        """
        创建WordPress用户
        
        Args:
            username: 用户名
            email: 邮箱地址
            
        Returns:
            新用户ID，创建失败返回None
        """
        try:
            # 生成16位随机密码
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/users",
                    json={
                        "username": username,
                        "email": email,
                        "password": password,
                        "roles": ["author"]
                    },
                    auth=(self.username, self.password)
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    user_id = result.get("id")
                    logger.info(f"成功创建WordPress用户: {username} (ID: {user_id})")
                    return user_id
                else:
                    logger.warning(f"创建WordPress用户失败: HTTP {response.status_code}, {response.text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"创建WordPress用户异常: {e}")
            return None

    def _extract_domain(self, url: str) -> str:
        """
        从URL提取域名
        
        Args:
            url: 完整URL
            
        Returns:
            域名（去掉www前缀）
        """
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # 去掉www前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    async def get_or_create_author(self, system_username: str, site_id: int, db) -> Optional[int]:
        """
        获取或创建WordPress作者
        
        流程：
        1. 查询缓存表
        2. 缓存未命中 -> 查询WordPress用户
        3. 用户不存在 -> 创建WordPress用户
        4. 保存到缓存
        
        Args:
            system_username: 系统用户名
            site_id: 站点ID
            db: 数据库会话
            
        Returns:
            WordPress用户ID，失败返回None
        """
        from sqlalchemy import select, text
        
        # 1. 查询缓存
        result = await db.execute(
            text("SELECT wp_user_id FROM wp_author_cache WHERE system_username = :username AND site_id = :site_id"),
            {"username": system_username, "site_id": site_id}
        )
        cached = result.fetchone()
        if cached:
            logger.info(f"使用缓存的WordPress作者ID: {cached[0]}")
            return cached[0]
        
        # 2. 查询WordPress用户
        wp_user_id = await self.get_user_by_username(system_username)
        
        # 3. 用户不存在，尝试创建
        if not wp_user_id:
            domain = self._extract_domain(self.site.url)
            email = f"{system_username}@{domain}"
            logger.info(f"WordPress用户不存在，尝试创建: {system_username} ({email})")
            wp_user_id = await self.create_user(system_username, email)
        
        # 4. 保存到缓存
        if wp_user_id:
            try:
                await db.execute(
                    text("""
                        INSERT INTO wp_author_cache (system_username, site_id, wp_user_id)
                        VALUES (:username, :site_id, :wp_user_id)
                        ON CONFLICT (system_username, site_id) DO UPDATE SET wp_user_id = :wp_user_id
                    """),
                    {"username": system_username, "site_id": site_id, "wp_user_id": wp_user_id}
                )
                await db.commit()
                logger.info(f"已缓存WordPress作者映射: {system_username} -> {wp_user_id}")
            except Exception as e:
                logger.error(f"保存作者缓存失败: {e}")
        
        return wp_user_id

    async def update_post(
        self,
        post_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        更新WordPress文章
        
        Args:
            post_id: 文章ID
            title: 新标题
            content: 新内容
            status: 新状态
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            post_data: Dict[str, Any] = {}
            
            if title is not None:
                post_data["title"] = title
            if content is not None:
                post_data["content"] = content
            if status is not None:
                post_data["status"] = status

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/posts/{post_id}",
                    json=post_data,
                    auth=(self.username, self.password)
                )
                
                if response.status_code == 200:
                    return True, None
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    return False, error_msg
                    
        except Exception as e:
            return False, f"更新错误: {str(e)}"

    async def get_post(self, post_id: int) -> tuple[bool, Optional[Dict], Optional[str]]:
        """
        获取WordPress文章
        
        Args:
            post_id: 文章ID
            
        Returns:
            (是否成功, 文章数据, 错误信息)
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/posts/{post_id}",
                    auth=(self.username, self.password) if self.username else None
                )
                
                if response.status_code == 200:
                    return True, response.json(), None
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    return False, None, error_msg
                    
        except Exception as e:
            return False, None, f"获取错误: {str(e)}"
