"""重复稿件 API"""
from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.duplicate_log import DuplicateLog
from app.api.dependencies import require_admin

router = APIRouter(prefix="/duplicate-logs", tags=["重复稿件"])


def _apply_filters(stmt, start_date: Optional[str], end_date: Optional[str], duplicate_type: Optional[str]):
    """应用日期和类型筛选（按 created_at）"""
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d").date()
            stmt = stmt.where(DuplicateLog.created_at >= datetime.combine(sd, time.min))
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d").date()
            stmt = stmt.where(DuplicateLog.created_at <= datetime.combine(ed, time.max))
        except ValueError:
            pass
    if duplicate_type:
        stmt = stmt.where(DuplicateLog.duplicate_type == duplicate_type)
    return stmt


@router.get("/")
async def list_duplicate_logs(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    duplicate_type: Optional[str] = Query(None, description="类型: skipped / superseded"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """获取重复稿件列表（分页、日期筛选），仅管理员"""
    base = select(DuplicateLog)
    base = _apply_filters(base, start_date, end_date, duplicate_type)

    count_stmt = select(func.count()).select_from(DuplicateLog)
    count_stmt = _apply_filters(count_stmt, start_date, end_date, duplicate_type)
    total = (await db.execute(count_stmt)).scalar_one()

    query = (
        base.order_by(DuplicateLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": x.id,
                "email_subject": x.email_subject,
                "email_from": x.email_from,
                "email_date": x.email_date.isoformat() if x.email_date else None,
                "cooperation_type": x.cooperation_type,
                "media_type": x.media_type,
                "source_unit": x.source_unit,
                "title": x.title,
                "duplicate_type": x.duplicate_type,
                "effective_submission_id": x.effective_submission_id,
                "superseded_submission_id": x.superseded_submission_id,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in items
        ],
        "total": total,
    }
