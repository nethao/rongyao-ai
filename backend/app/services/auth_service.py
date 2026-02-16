"""
认证服务
"""
from typing import Optional, Tuple, List
from sqlalchemy import select, func
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
    
    async def list_users(
        self,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[User], int]:
        """
        分页获取用户列表（不含密码）

        Returns:
            (用户列表, 总数)
        """
        count_result = await self.db.execute(select(func.count(User.id)))
        total = count_result.scalar_one()
        offset = (page - 1) * size
        result = await self.db.execute(
            select(User).order_by(User.id.asc()).offset(offset).limit(size)
        )
        users = result.scalars().all()
        return users, total

    async def update_user(
        self, 
        user_id: int, 
        role: str,
        wp_author_id: Optional[int] = None
    ) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            role: 新角色（admin 或 editor）
            wp_author_id: WordPress作者ID（可选）

        Returns:
            更新后的用户，不存在则返回 None
        """
        if role not in ("admin", "editor"):
            raise ValueError("角色必须是 admin 或 editor")
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        user.role = role
        if wp_author_id is not None:
            user.wp_author_id = wp_author_id
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: int, current_user_id: int) -> None:
        """
        删除用户。不能删除自己，不能删除最后一个管理员。

        Raises:
            ValueError: 不允许删除时
        """
        if user_id == current_user_id:
            raise ValueError("不能删除当前登录用户")
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        if user.role == "admin":
            count_result = await self.db.execute(
                select(func.count(User.id)).where(User.role == "admin")
            )
            admin_count = count_result.scalar_one()
            if admin_count <= 1:
                raise ValueError("不能删除唯一的管理员")
        self.db.delete(user)
        await self.db.commit()

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
