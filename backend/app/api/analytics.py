"""
数据分析API

稿件统计时间规则：日期 D 的稿件 = (D-1)日 14:01 至 D日 14:00 之间创建/发布。
例如：1月1日 14:01 至 1月2日 14:00 归为 1月2日；按北京时间。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta, date
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.api.dependencies import require_admin
from app.services.byline_service import BylineService

router = APIRouter(prefix="/analytics", tags=["analytics"])

# 排除被新稿替换的旧稿（duplicate_logs.superseded_submission_id）
_SUPERSEDED_EXCLUSION = "id NOT IN (SELECT superseded_submission_id FROM duplicate_logs WHERE superseded_submission_id IS NOT NULL)"

# 北京时间（Asia/Shanghai）下：stat_date = 若 time >= 14:01 则 date+1 否则 date
def _stat_date_expr(alias: str = "created_at") -> str:
    return (
        f"(({alias} AT TIME ZONE 'Asia/Shanghai')::date + "
        f"CASE WHEN (({alias} AT TIME ZONE 'Asia/Shanghai')::time >= time '14:01:00') THEN 1 ELSE 0 END)"
    )


_STAT_DATE_EXPR = _stat_date_expr("created_at")
_PH_STAT_DATE_EXPR = _stat_date_expr("ph.created_at")
# 采编工作量：按邮件到达邮箱时间（email_date），无则用 created_at）
_EMAIL_STAT_DATE_EXPR = _stat_date_expr("COALESCE(email_date, created_at)")


def _date_filter_sql(stat_date_expr: str, start_date: Optional[str], end_date: Optional[str], params: dict) -> str:
    """生成时间范围条件：stat_date 在 [start_date, end_date] 内。asyncpg 需要 date 对象。"""
    clause = ""
    if start_date:
        clause += f" AND ({stat_date_expr}) >= CAST(:start_date AS date)"
        params["start_date"] = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        clause += f" AND ({stat_date_expr}) <= CAST(:end_date AS date)"
        params["end_date"] = datetime.strptime(end_date, "%Y-%m-%d").date()
    return clause


@router.get("/overview")
async def get_overview(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取概览统计（按 14:01~次日14:00 归日规则）"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION}"
    params = {}
    where_clause += _date_filter_sql(_STAT_DATE_EXPR, start_date, end_date, params)

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
    current_user: User = Depends(require_admin)
):
    """获取投稿趋势统计（按 14:01~次日14:00 归日，按统计日分组）"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION}"
    params = {}
    where_clause += _date_filter_sql(_STAT_DATE_EXPR, start_date, end_date, params)

    result = await db.execute(
        text(f"""
            SELECT 
                {_STAT_DATE_EXPR} as date,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE id IN (
                    SELECT DISTINCT submission_id FROM drafts WHERE status = 'published'
                )) as published,
                ROUND(COUNT(*) FILTER (WHERE status = 'completed')::numeric / NULLIF(COUNT(*), 0) * 100, 1) as completion_rate
            FROM submissions
            {where_clause}
            GROUP BY {_STAT_DATE_EXPR}
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
    current_user: User = Depends(require_admin)
):
    """获取采编投稿统计。采编=来稿邮件地址，显示名=后台姓名映射，无映射显示邮箱。时间按 14:01~次日14:00 归日。"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION} AND email_from IS NOT NULL"
    params = {}
    where_clause += _date_filter_sql(_STAT_DATE_EXPR, start_date, end_date, params)

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
    rows = result.fetchall()
    byline_svc = BylineService(db)
    stats = []
    for row in rows:
        display_name = await byline_svc.get_editor_display_name(row.editor)
        stats.append({
            "editor": (display_name or row.editor or "").strip() or row.editor,
            "total": row.total,
            "pending": row.pending,
            "completed": row.completed,
            "published": row.published,
            "completion_rate": float(row.completion_rate) if row.completion_rate else 0,
            "publish_rate": float(row.publish_rate) if row.publish_rate else 0
        })
    return stats


@router.get("/editor-options")
async def get_editor_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """采编人员下拉选项：返回所有出现过的来稿邮箱及显示名（供采编工作量页筛选）。"""
    result = await db.execute(
        text(f"""
            SELECT DISTINCT email_from
            FROM submissions
            WHERE {_SUPERSEDED_EXCLUSION} AND email_from IS NOT NULL AND email_from != ''
            ORDER BY email_from
            LIMIT 500
        """)
    )
    rows = result.fetchall()
    byline_svc = BylineService(db)
    options = []
    for row in rows:
        display_name = await byline_svc.get_editor_display_name(row.email_from)
        options.append({
            "email_from": row.email_from,
            "label": (display_name or row.email_from or "").strip() or row.email_from
        })
    return options


@router.get("/editor-workload")
async def get_editor_workload(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    email_from: Optional[str] = Query(None, description="采编人员：按来稿邮箱筛选"),
    media_type: Optional[str] = Query(None, description="媒体站点：rongyao/shidai/zhengxian/zhengqi/toutiao"),
    cooperation_type: Optional[str] = Query(None, description="合作方式：free=投，partner=合"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """采编工作量统计（独立页）：按邮件到达邮箱时间（email_date）的 14:01~次日14:00 归日，可选按采编、媒体站点、合作方式筛选。"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION} AND email_from IS NOT NULL"
    params = {}
    where_clause += _date_filter_sql(_EMAIL_STAT_DATE_EXPR, start_date, end_date, params)
    if email_from:
        where_clause += " AND email_from = :email_from"
        params["email_from"] = email_from
    if media_type:
        where_clause += " AND media_type = :media_type"
        params["media_type"] = media_type
    if cooperation_type:
        where_clause += " AND cooperation_type = :cooperation_type"
        params["cooperation_type"] = cooperation_type

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
    rows = result.fetchall()
    byline_svc = BylineService(db)
    stats = []
    for row in rows:
        display_name = await byline_svc.get_editor_display_name(row.editor)
        stats.append({
            "editor": (display_name or row.editor or "").strip() or row.editor,
            "email_from": row.editor,  # 原始邮箱，供前端采编筛选下拉使用
            "total": row.total,
            "pending": row.pending,
            "completed": row.completed,
            "published": row.published,
            "completion_rate": float(row.completion_rate) if row.completion_rate else 0,
            "publish_rate": float(row.publish_rate) if row.publish_rate else 0
        })
    return stats


@router.get("/editor-workload-detail")
async def get_editor_workload_detail(
    email_from: str = Query(..., description="采编来稿邮箱"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """采编详细工作量：指定采编在时间范围内的投稿数、按站点分布、投/合数量。"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION} AND email_from = :email_from"
    params = {"email_from": email_from}
    where_clause += _date_filter_sql(_EMAIL_STAT_DATE_EXPR, start_date, end_date, params)

    byline_svc = BylineService(db)
    display_name = await byline_svc.get_editor_display_name(email_from)
    editor_label = (display_name or email_from or "").strip() or email_from

    # 汇总
    r1 = await db.execute(
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
    row1 = r1.fetchone()
    # 按媒体站点（投稿的 media_type）
    r2 = await db.execute(
        text(f"""
            SELECT media_type, COUNT(*) as count
            FROM submissions
            {where_clause}
            AND media_type IS NOT NULL
            GROUP BY media_type
            ORDER BY count DESC
        """),
        params
    )
    by_media_rows = r2.fetchall()
    # 查 media_type -> 站点名称（媒体映射表 + wordpress_sites）
    r2b = await db.execute(
        text("""
            SELECT m.media_type, ws.name as site_name
            FROM media_site_mappings m
            LEFT JOIN wordpress_sites ws ON ws.id = m.site_id
        """)
    )
    media_to_site_name = {r.media_type: r.site_name for r in r2b.fetchall() if r.media_type}
    by_media = [
        {
            "media_type": r.media_type,
            "count": r.count,
            "site_name": media_to_site_name.get(r.media_type),
        }
        for r in by_media_rows
    ]
    # 按合作方式
    r3 = await db.execute(
        text(f"""
            SELECT cooperation_type, COUNT(*) as count
            FROM submissions
            {where_clause}
            AND cooperation_type IS NOT NULL
            GROUP BY cooperation_type
            ORDER BY count DESC
        """),
        params
    )
    by_cooperation = [{"cooperation_type": r.cooperation_type, "count": r.count} for r in r3.fetchall()]

    return {
        "editor": editor_label,
        "email_from": email_from,
        "total": row1.total or 0,
        "pending": row1.pending or 0,
        "completed": row1.completed or 0,
        "published": row1.published or 0,
        "by_media_type": by_media,
        "by_cooperation_type": by_cooperation,
    }


@router.get("/copy-editor-workload-detail")
async def get_copy_editor_workload_detail(
    publisher_user_id: int = Query(..., description="文编 user_id"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """文编详细工作量：指定文编在时间范围内的发布量、按站点分布。"""
    where_clause = "WHERE ph.status = 'success' AND ph.publisher_user_id = :publisher_user_id"
    params = {"publisher_user_id": publisher_user_id}
    where_clause += _date_filter_sql(_PH_STAT_DATE_EXPR, start_date, end_date, params)

    # 文编名称
    r0 = await db.execute(
        text("SELECT COALESCE(display_name, username) as name FROM users WHERE id = :uid"),
        {"uid": publisher_user_id}
    )
    urow = r0.fetchone()
    copy_editor_label = (urow.name if urow else None) or "未记录"

    # 总发布量
    r1 = await db.execute(
        text(f"""
            SELECT COUNT(*) as published
            FROM publish_history ph
            {where_clause}
        """),
        params
    )
    row1 = r1.fetchone()
    total = row1.published if row1 else 0
    # 按站点
    r2 = await db.execute(
        text(f"""
            SELECT ph.site_id, ws.name as site_name, COUNT(*) as published
            FROM publish_history ph
            JOIN wordpress_sites ws ON ph.site_id = ws.id
            {where_clause}
            GROUP BY ph.site_id, ws.name
            ORDER BY published DESC
        """),
        params
    )
    by_site = [{"site_id": r.site_id, "site_name": r.site_name, "published": r.published} for r in r2.fetchall()]

    return {
        "copy_editor": copy_editor_label,
        "publisher_user_id": publisher_user_id,
        "total_published": total,
        "by_site": by_site,
    }


@router.get("/media")
async def get_media_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取媒体类型统计（以网站媒体分析采编投稿件数，时间按 14:01~次日14:00 归日）"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION} AND media_type IS NOT NULL"
    params = {}
    where_clause += _date_filter_sql(_STAT_DATE_EXPR, start_date, end_date, params)

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
    current_user: User = Depends(require_admin)
):
    """获取来稿单位统计（时间按 14:01~次日14:00 归日）"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION} AND source_unit IS NOT NULL"
    params = {}
    where_clause += _date_filter_sql(_STAT_DATE_EXPR, start_date, end_date, params)

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
    current_user: User = Depends(require_admin)
):
    """获取编辑人员统计（时间按 14:01~次日14:00 归日）"""
    where_clause = "WHERE s.id NOT IN (SELECT superseded_submission_id FROM duplicate_logs WHERE superseded_submission_id IS NOT NULL)"
    params = {}
    where_clause += _date_filter_sql(_PH_STAT_DATE_EXPR, start_date, end_date, params)

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


@router.get("/copy-editor-options")
async def get_copy_editor_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """文编人员下拉选项：在 publish_history 中出现过的发布人（供文编工作量筛选）。"""
    result = await db.execute(
        text("""
            SELECT DISTINCT ph.publisher_user_id as user_id,
                   COALESCE(u.display_name, u.username, '未记录') as label
            FROM publish_history ph
            LEFT JOIN users u ON u.id = ph.publisher_user_id
            WHERE ph.status = 'success' AND ph.publisher_user_id IS NOT NULL
            ORDER BY label
            LIMIT 200
        """)
    )
    rows = result.fetchall()
    return [{"user_id": row.user_id, "label": row.label or "未记录"} for row in rows]


@router.get("/copy-editors")
async def get_copy_editor_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    publisher_user_id: Optional[int] = Query(None, description="文编人员（发布人 user_id）"),
    site_id: Optional[int] = Query(None, description="发布站点 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """文编工作量统计：按发布人统计发布量，时间按 14:01~次日14:00 归日；可选按文编、发布站点筛选。"""
    where_clause = "WHERE ph.status = 'success'"
    params = {}
    where_clause += _date_filter_sql(_PH_STAT_DATE_EXPR, start_date, end_date, params)
    if publisher_user_id is not None:
        where_clause += " AND ph.publisher_user_id = :publisher_user_id"
        params["publisher_user_id"] = publisher_user_id
    if site_id is not None:
        where_clause += " AND ph.site_id = :site_id"
        params["site_id"] = site_id
    result = await db.execute(
        text(f"""
            SELECT 
                ph.publisher_user_id,
                COALESCE(u.display_name, u.username, '未记录') as copy_editor,
                COUNT(*) as published
            FROM publish_history ph
            LEFT JOIN users u ON u.id = ph.publisher_user_id
            {where_clause}
            GROUP BY ph.publisher_user_id, u.id, u.display_name, u.username
            ORDER BY published DESC
        """),
        params
    )
    stats = []
    for row in result:
        stats.append({
            "copy_editor": row.copy_editor or "未记录",
            "publisher_user_id": row.publisher_user_id,
            "published": row.published
        })
    return stats


@router.get("/sites")
async def get_site_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取站点发布统计（时间按 14:01~次日14:00 归日）"""
    where_clause = "WHERE 1=1"
    params = {}
    where_clause += _date_filter_sql(_PH_STAT_DATE_EXPR, start_date, end_date, params)

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
    current_user: User = Depends(require_admin)
):
    """获取内容来源统计（时间按 14:01~次日14:00 归日）"""
    where_clause = f"WHERE {_SUPERSEDED_EXCLUSION} AND content_source IS NOT NULL"
    params = {}
    where_clause += _date_filter_sql(_STAT_DATE_EXPR, start_date, end_date, params)

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
