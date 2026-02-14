"""
WordPress REST API客户端服务
"""
import httpx
from typing import Optional, Dict, Any
from app.models.wordpress_site import WordPressSite


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
        tags: Optional[list[int]] = None
    ) -> tuple[bool, Optional[int], Optional[str]]:
        """
        创建WordPress文章
        
        Args:
            title: 文章标题
            content: 文章内容（HTML格式）
            status: 文章状态 ('draft', 'publish', 'pending')
            categories: 分类ID列表
            tags: 标签ID列表
            
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
