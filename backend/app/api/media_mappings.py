from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.media_site_mapping import MediaSiteMapping
from app.api.auth import get_current_user

from pydantic import BaseModel

# 各媒体类型 ID（media_type）及中文名称，与邮件解析、投稿统计一致
MEDIA_TYPE_IDS = [
    {"media_type": "rongyao", "name": "荣耀网"},
    {"media_type": "shidai", "name": "时代网"},
    {"media_type": "zhengxian", "name": "争先网"},
    {"media_type": "zhengqi", "name": "政企网"},
    {"media_type": "toutiao", "name": "今日头条"},
]

class MediaMappingUpdate(BaseModel):
    site_id: int

router = APIRouter(prefix="/media-mappings", tags=["media-mappings"])


@router.get("/ids")
async def get_media_type_ids(
    current_user: User = Depends(get_current_user)
):
    """返回各媒体的类型 ID（media_type）及名称；不包含站点映射，仅作对照表。"""
    return MEDIA_TYPE_IDS


@router.get("/with-sites")
async def get_media_mappings_with_sites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取媒体 ↔ 站点映射：各媒体 ID、名称及当前映射的站点 ID、站点名称。"""
    name_by_type = {m["media_type"]: m["name"] for m in MEDIA_TYPE_IDS}
    result = await db.execute(
        select(MediaSiteMapping).options(selectinload(MediaSiteMapping.site))
    )
    mappings = result.scalars().unique().all()
    map_by_media = {m.media_type: m for m in mappings}
    out = []
    for m in MEDIA_TYPE_IDS:
        mt = m["media_type"]
        rec = {"media_type": mt, "name": m["name"], "site_id": None, "site_name": None}
        mapping = map_by_media.get(mt)
        if mapping and mapping.site_id and mapping.site:
            rec["site_id"] = mapping.site_id
            rec["site_name"] = mapping.site.name
        out.append(rec)
    return out


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
