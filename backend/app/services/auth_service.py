"""
认证服务
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.utils.auth import verify_password, get_password_hash


class AuthService:
    """用户认证和授权服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        验证用户凭证
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            Optional[User]: 验证成功返回用户对象，失败返回None
        """
        # 查找用户
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # 验证密码
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        根据ID获取用户
        
        Args:
            user_id: 用户ID
        
        Returns:
            Optional[User]: 用户对象
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
        
        Returns:
            Optional[User]: 用户对象
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "editor"
    ) -> User:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            role: 角色（admin或editor）
        
        Returns:
            User: 创建的用户对象
        """
        # 检查用户名是否已存在
        existing_user = await self.get_user_by_username(username)
        if existing_user:
            raise ValueError(f"用户名 '{username}' 已存在")
        
        # 创建用户
        user = User(
            username=username,
            password_hash=get_password_hash(password),
            role=role
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def update_password(
        self,
        user_id: int,
        new_password: str
    ) -> bool:
        """
        更新用户密码
        
        Args:
            user_id: 用户ID
            new_password: 新密码
        
        Returns:
            bool: 是否更新成功
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        
        return True
    
    def check_permission(self, user: User, resource: str, action: str) -> bool:
        """
        检查用户权限
        
        Args:
            user: 用户对象
            resource: 资源名称
            action: 操作类型
        
        Returns:
            bool: 是否有权限
        """
        # 管理员拥有所有权限
        if user.role == "admin":
            return True
        
        # 编辑人员权限规则
        if user.role == "editor":
            # 编辑人员可以访问审核和发布功能
            allowed_resources = ["submissions", "drafts", "publish"]
            return resource in allowed_resources
        
        return False
