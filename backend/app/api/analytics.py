"""
数据分析API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取概览统计"""
    where_clause = "WHERE 1=1"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                )) as published
            FROM submissions
            {where_clause}
        """),
        params
    )
    row = result.fetchone()
    
    return {
        "total": row.total,
        "pending": row.pending,
        "completed": row.completed,
        "published": row.published
    }


@router.get("/trends")
async def get_trends(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取投稿趋势统计"""
    where_clause = "WHERE 1=1"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                )) as published,
                ROUND(COUNT(*) FILTER (WHERE status = 'completed')::numeric / NULLIF(COUNT(*), 0) * 100, 1) as completion_rate
            FROM submissions
            {where_clause}
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """),
        params
    )
    
    trends = []
    for row in result:
        trends.append({
            "date": row.date.isoformat() if row.date else None,
            "total": row.total,
            "completed": row.completed,
            "published": row.published,
            "completion_rate": float(row.completion_rate) if row.completion_rate else 0
        })
    
    return trends


@router.get("/editors")
async def get_editor_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取采编投稿统计"""
    where_clause = "WHERE email_from IS NOT NULL"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                email_from as editor,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                )) as published,
                ROUND(COUNT(*) FILTER (WHERE status = 'completed')::numeric / NULLIF(COUNT(*), 0) * 100, 1) as completion_rate,
                ROUND(COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                ))::numeric / NULLIF(COUNT(*), 0) * 100, 1) as publish_rate
            FROM submissions
            {where_clause}
            GROUP BY email_from
            ORDER BY total DESC
        """),
        params
    )
    
    stats = []
    for row in result:
        stats.append({
            "editor": row.editor,
            "total": row.total,
            "pending": row.pending,
            "completed": row.completed,
            "published": row.published,
            "completion_rate": float(row.completion_rate) if row.completion_rate else 0,
            "publish_rate": float(row.publish_rate) if row.publish_rate else 0
        })
    
    return stats


@router.get("/media")
async def get_media_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取媒体类型统计"""
    where_clause = "WHERE media_type IS NOT NULL"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                media_type,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                )) as published,
                ROUND(COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                ))::numeric / NULLIF(COUNT(*), 0) * 100, 1) as publish_rate
            FROM submissions
            {where_clause}
            GROUP BY media_type
            ORDER BY total DESC
        """),
        params
    )
    
    stats = []
    for row in result:
        stats.append({
            "media_type": row.media_type,
            "total": row.total,
            "published": row.published,
            "publish_rate": float(row.publish_rate) if row.publish_rate else 0
        })
    
    return stats


@router.get("/units")
async def get_unit_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取来稿单位统计"""
    where_clause = "WHERE source_unit IS NOT NULL"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                source_unit,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                )) as published,
                ROUND(COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                ))::numeric / NULLIF(COUNT(*), 0) * 100, 1) as publish_rate
            FROM submissions
            {where_clause}
            GROUP BY source_unit
            ORDER BY total DESC
        """),
        params
    )
    
    stats = []
    for row in result:
        stats.append({
            "unit": row.source_unit,
            "total": row.total,
            "published": row.published,
            "publish_rate": float(row.publish_rate) if row.publish_rate else 0
        })
    
    return stats


@router.get("/users")
async def get_user_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取编辑人员统计"""
    where_clause = "WHERE 1=1"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(ph.created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(ph.created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                u.username,
                COUNT(DISTINCT ph.draft_id) as processed,
                COUNT(DISTINCT ph.draft_id) FILTER (WHERE ph.status = 'success') as published,
                ROUND(AVG(EXTRACT(EPOCH FROM (ph.created_at - d.created_at)) / 3600), 1) as avg_hours
            FROM publish_history ph
            JOIN drafts d ON ph.draft_id = d.id
            JOIN submissions s ON d.submission_id = s.id
            JOIN users u ON u.username = s.email_from
            {where_clause}
            GROUP BY u.username
            ORDER BY processed DESC
        """),
        params
    )
    
    stats = []
    for row in result:
        stats.append({
            "username": row.username,
            "processed": row.processed,
            "published": row.published,
            "avg_hours": float(row.avg_hours) if row.avg_hours else 0
        })
    
    return stats


@router.get("/sites")
async def get_site_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取站点发布统计"""
    where_clause = "WHERE 1=1"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(ph.created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(ph.created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                ws.name as site_name,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE ph.status = 'success') as success,
                COUNT(*) FILTER (WHERE ph.status = 'failed') as failed,
                ROUND(COUNT(*) FILTER (WHERE ph.status = 'success')::numeric / NULLIF(COUNT(*), 0) * 100, 1) as success_rate
            FROM publish_history ph
            JOIN wordpress_sites ws ON ph.site_id = ws.id
            {where_clause}
            GROUP BY ws.name
            ORDER BY total DESC
        """),
        params
    )
    
    stats = []
    for row in result:
        stats.append({
            "site_name": row.site_name,
            "total": row.total,
            "success": row.success,
            "failed": row.failed,
            "success_rate": float(row.success_rate) if row.success_rate else 0
        })
    
    return stats


@router.get("/sources")
async def get_source_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取内容来源统计"""
    where_clause = "WHERE content_source IS NOT NULL"
    params = {}
    
    if start_date:
        where_clause += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where_clause += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    result = await db.execute(
        text(f"""
            SELECT 
                content_source,
                COUNT(*) as total,
                ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM submissions {where_clause}) * 100, 1) as percentage
            FROM submissions
            {where_clause}
            GROUP BY content_source
            ORDER BY total DESC
        """),
        params
    )
    
    stats = []
    for row in result:
        stats.append({
            "source": row.content_source,
            "total": row.total,
            "percentage": float(row.percentage) if row.percentage else 0
        })
    
    return stats
