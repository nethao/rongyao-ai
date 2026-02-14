"""
权限检查工具
"""
from enum import Enum
from typing import List
from app.models.user import User


class Role(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    EDITOR = "editor"


class Resource(str, Enum):
    """资源类型枚举"""
    CONFIG = "config"
    USERS = "users"
    SUBMISSIONS = "submissions"
    DRAFTS = "drafts"
    WORDPRESS_SITES = "wordpress_sites"
    PUBLISH = "publish"
    LOGS = "logs"


class Action(str, Enum):
    """操作类型枚举"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"


# 权限规则定义
PERMISSION_RULES = {
    Role.ADMIN: {
        # 管理员拥有所有权限
        Resource.CONFIG: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE],
        Resource.USERS: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE],
        Resource.SUBMISSIONS: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE],
        Resource.DRAFTS: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE],
        Resource.WORDPRESS_SITES: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE],
        Resource.PUBLISH: [Action.EXECUTE],
        Resource.LOGS: [Action.READ],
    },
    Role.EDITOR: {
        # 编辑人员只能访问审核和发布功能
        Resource.SUBMISSIONS: [Action.READ],
        Resource.DRAFTS: [Action.READ, Action.UPDATE],
        Resource.WORDPRESS_SITES: [Action.READ],
        Resource.PUBLISH: [Action.EXECUTE],
    }
}


def check_permission(user: User, resource: Resource, action: Action) -> bool:
    """
    检查用户是否有权限执行指定操作
    
    Args:
        user: 用户对象
        resource: 资源类型
        action: 操作类型
    
    Returns:
        bool: 是否有权限
    """
    if not user:
        return False
    
    # 获取用户角色的权限规则
    role = Role(user.role)
    role_permissions = PERMISSION_RULES.get(role, {})
    
    # 检查资源权限
    allowed_actions = role_permissions.get(resource, [])
    return action in allowed_actions


def get_user_permissions(user: User) -> dict:
    """
    获取用户的所有权限
    
    Args:
        user: 用户对象
    
    Returns:
        dict: 权限字典
    """
    if not user:
        return {}
    
    role = Role(user.role)
    return PERMISSION_RULES.get(role, {})


def require_permission(resource: Resource, action: Action):
    """
    权限检查装饰器工厂
    
    Args:
        resource: 资源类型
        action: 操作类型
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user
            current_user = kwargs.get('current_user')
            
            if not current_user:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )
            
            if not check_permission(current_user, resource, action):
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"没有权限执行此操作: {resource.value}/{action.value}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
