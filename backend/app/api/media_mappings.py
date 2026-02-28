from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.media_site_mapping import MediaSiteMapping
from app.api.auth import get_current_user

from pydantic import BaseModel

class MediaMappingUpdate(BaseModel):
    site_id: int

router = APIRouter(prefix="/media-mappings", tags=["media-mappings"])


@router.get("")
async def get_media_mappings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有媒体类型与站点的映射"""
    result = await db.execute(select(MediaSiteMapping))
    mappings = result.scalars().all()
    return [
        {
            "id": m.id,
            "media_type": m.media_type,
            "site_id": m.site_id,
            "created_at": m.created_at,
            "updated_at": m.updated_at
        }
        for m in mappings
    ]


@router.put("/{media_type}")
async def update_media_mapping(
    media_type: str,
    data: MediaMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新或创建媒体类型与站点的映射"""
    result = await db.execute(
        select(MediaSiteMapping).where(MediaSiteMapping.media_type == media_type)
    )
    mapping = result.scalar_one_or_none()
    
    if mapping:
        mapping.site_id = data.site_id
    else:
        mapping = MediaSiteMapping(media_type=media_type, site_id=data.site_id)
        db.add(mapping)
    
    await db.commit()
    await db.refresh(mapping)
    
    return {
        "id": mapping.id,
        "media_type": mapping.media_type,
        "site_id": mapping.site_id
    }


@router.delete("/{media_type}")
async def delete_media_mapping(
    media_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除媒体类型与站点的映射"""
    result = await db.execute(
        select(MediaSiteMapping).where(MediaSiteMapping.media_type == media_type)
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="映射不存在")
    
    await db.delete(mapping)
    await db.commit()
    
    return {"success": True}
