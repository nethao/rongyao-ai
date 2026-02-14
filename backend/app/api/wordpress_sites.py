"""
WordPress站点管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.api.dependencies import get_current_user, require_admin
from app.services.wordpress_site_service import WordPressSiteService
from app.services.wordpress_service import WordPressService
from app.schemas.wordpress import (
    WordPressSite,
    WordPressSiteCreate,
    WordPressSiteUpdate,
    WordPressSiteList
)
from pydantic import BaseModel


class VerifyResult(BaseModel):
    """验证结果"""
    valid: bool
    message: Optional[str] = None

router = APIRouter(prefix="/wordpress-sites", tags=["WordPress站点"])


@router.post("", response_model=WordPressSite, status_code=status.HTTP_201_CREATED)
async def create_wordpress_site(
    site_data: WordPressSiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    创建WordPress站点（仅管理员）
    """
    service = WordPressSiteService(db)
    site = await service.create_site(site_data)
    return site


@router.get("", response_model=WordPressSiteList)
async def list_wordpress_sites(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取WordPress站点列表
    """
    service = WordPressSiteService(db)
    sites = await service.list_sites(active_only=active_only)
    return WordPressSiteList(sites=sites, total=len(sites))


@router.get("/{site_id}", response_model=WordPressSite)
async def get_wordpress_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取WordPress站点详情
    """
    service = WordPressSiteService(db)
    site = await service.get_site(site_id)
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在"
        )
    
    return site


@router.put("/{site_id}", response_model=WordPressSite)
async def update_wordpress_site(
    site_id: int,
    site_data: WordPressSiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    更新WordPress站点（仅管理员）
    """
    service = WordPressSiteService(db)
    site = await service.update_site(site_id, site_data)
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在"
        )
    
    return site


@router.post("/{site_id}/test", response_model=VerifyResult)
async def test_wordpress_connection(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试WordPress站点连接
    """
    site_service = WordPressSiteService(db)
    site = await site_service.get_site(site_id)
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在"
        )
    
    # 获取解密后的密码
    password = site_service.get_decrypted_password(site)
    
    if not site.api_username or not password:
        return VerifyResult(
            valid=False,
            message="站点缺少用户名或密码配置"
        )
    
    # 测试连接
    wp_service = WordPressService(site, password)
    try:
        success, message = await wp_service.verify_connection()
        return VerifyResult(
            valid=success,
            message=message or ("连接成功" if success else "连接失败")
        )
    except Exception as e:
        return VerifyResult(
            valid=False,
            message=f"连接失败: {str(e)}"
        )



@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wordpress_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    删除WordPress站点（仅管理员）
    """
    service = WordPressSiteService(db)
    success = await service.delete_site(site_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在"
        )
    
    return None


@router.post("/{site_id}/verify", response_model=VerifyResult)
async def verify_wordpress_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    验证WordPress站点连接（仅管理员）
    """
    site_service = WordPressSiteService(db)
    site = await site_service.get_site(site_id)
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在"
        )
    
    # 获取解密后的密码
    api_password = site_service.get_decrypted_password(site)
    
    if not api_password:
        return VerifyResult(valid=False, message="未配置API密码")
    
    # 验证连接
    wp_service = WordPressService(site, api_password)
    success, error_msg = await wp_service.verify_connection()
    
    if success:
        return VerifyResult(valid=True, message="连接成功")
    else:
        return VerifyResult(valid=False, message=error_msg)
