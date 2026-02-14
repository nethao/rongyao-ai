"""
认证API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    User as UserSchema,
    MessageResponse,
    PasswordChangeRequest
)
from app.utils.auth import create_access_token
from app.models.user import User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    """
    auth_service = AuthService(db)
    user = await auth_service.authenticate(
        username=login_data.username,
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 生成JWT令牌
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserSchema.model_validate(user)
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    用户登出
    
    注意：JWT是无状态的，实际的登出需要在客户端删除令牌
    """
    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return UserSchema.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密码
    """
    auth_service = AuthService(db)
    
    # 验证旧密码
    user = await auth_service.authenticate(
        username=current_user.username,
        password=password_data.old_password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    success = await auth_service.update_password(
        user_id=current_user.id,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码更新失败"
        )
    
    return MessageResponse(message="密码修改成功")
