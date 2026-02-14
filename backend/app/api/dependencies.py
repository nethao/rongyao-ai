"""
API依赖注入函数
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.utils.auth import decode_access_token
from app.utils.permissions import Resource, Action, check_permission

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前登录用户
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌格式",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户（可扩展添加用户状态检查）
    """
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    要求管理员权限
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


async def require_editor(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    要求编辑人员或管理员权限
    """
    if current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要编辑人员或管理员权限"
        )
    return current_user


def require_permission(resource: Resource, action: Action):
    """
    权限检查依赖工厂
    
    Args:
        resource: 资源类型
        action: 操作类型
    
    Returns:
        依赖函数
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not check_permission(current_user, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有权限执行此操作: {resource.value}/{action.value}"
            )
        return current_user
    
    return permission_checker
