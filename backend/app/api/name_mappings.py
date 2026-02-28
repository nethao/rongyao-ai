"""
采编/文编名称映射 API（管理员 CRUD + 编辑个人文编映射与密码）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.editor_name_mapping import EditorNameMapping
from app.models.copy_editor_site_mapping import CopyEditorSiteMapping
from app.models.wordpress_site import WordPressSite
from app.api.dependencies import get_current_user, require_admin
from app.services.auth_service import AuthService
from app.schemas.name_mapping import (
    EditorNameMappingSchema,
    EditorNameMappingCreate,
    EditorNameMappingUpdate,
    CopyEditorSiteMappingSchema,
    CopyEditorSiteMappingCreate,
    CopyEditorSiteMappingUpdate,
)
from app.schemas.auth import MessageResponse, PasswordChangeRequest

router = APIRouter(prefix="/name-mappings", tags=["名称映射"])


# ---------- 个人资料（固定路径放最前，避免被 /{id} 类路由匹配） ----------
@router.get("/my/profile")
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户资料：基本信息 + 文编站点映射列表"""
    r = await db.execute(
        select(CopyEditorSiteMapping)
        .where(CopyEditorSiteMapping.user_id == current_user.id)
        .options(selectinload(CopyEditorSiteMapping.site))
        .order_by(CopyEditorSiteMapping.site_id)
    )
    mappings = r.scalars().all()
    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
            "display_name": current_user.display_name,
        },
        "copy_editor_mappings": [CopyEditorSiteMappingSchema(**_copy_editor_with_site_name(x)) for x in mappings],
    }


@router.post("/my/change-password", response_model=MessageResponse)
async def change_my_password(
    body: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户修改自己的密码"""
    auth_service = AuthService(db)
    user = await auth_service.authenticate(current_user.username, body.old_password)
    if not user:
        raise HTTPException(status_code=400, detail="旧密码错误")
    success = await auth_service.update_password(user.id, body.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="密码更新失败")
    return MessageResponse(message="密码修改成功")


# ---------- 采编映射（管理员） ----------
@router.get("/editor-email-options")
async def get_editor_email_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """供采编映射「邮箱/前缀」下拉使用：投稿历史中的发件人 + 已配置的邮箱，去重"""
    from app.models.submission import Submission

    # 投稿表中出现过的 email_from（去重，最多 200 条）
    r = await db.execute(
        select(Submission.email_from)
        .where(Submission.email_from.isnot(None), Submission.email_from != "")
        .distinct()
        .limit(200)
    )
    from_submissions = [x for x in r.scalars().all() if x]
    # 已配置的采编映射邮箱
    r2 = await db.execute(select(EditorNameMapping.email).order_by(EditorNameMapping.email))
    from_mappings = list(r2.scalars().all())
    # 合并去重，映射在前
    seen = set()
    result = []
    for e in from_mappings + from_submissions:
        e = (e or "").strip()
        if e and e not in seen:
            seen.add(e)
            result.append(e)
    return result


@router.get("/editors", response_model=List[EditorNameMappingSchema])
async def list_editor_mappings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """采编映射列表（邮箱 -> 采编姓名）"""
    r = await db.execute(select(EditorNameMapping).order_by(EditorNameMapping.email))
    return r.scalars().all()


@router.post("/editors", response_model=EditorNameMappingSchema, status_code=status.HTTP_201_CREATED)
async def create_editor_mapping(
    body: EditorNameMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """新增采编映射"""
    email = (body.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="邮箱不能为空")
    r = await db.execute(select(EditorNameMapping).where(EditorNameMapping.email == email).limit(1))
    if r.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已存在映射")
    m = EditorNameMapping(email=email, display_name=(body.display_name or "").strip())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


@router.put("/editors/{mapping_id}", response_model=EditorNameMappingSchema)
async def update_editor_mapping(
    mapping_id: int,
    body: EditorNameMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新采编映射"""
    r = await db.execute(select(EditorNameMapping).where(EditorNameMapping.id == mapping_id).limit(1))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="映射不存在")
    m.display_name = (body.display_name or "").strip()
    await db.commit()
    await db.refresh(m)
    return m


@router.delete("/editors/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_editor_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """删除采编映射"""
    r = await db.execute(select(EditorNameMapping).where(EditorNameMapping.id == mapping_id).limit(1))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="映射不存在")
    await db.delete(m)
    await db.commit()


# ---------- 文编站点映射（管理员：全部；编辑：仅自己） ----------
def _copy_editor_with_site_name(row: CopyEditorSiteMapping) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "site_id": row.site_id,
        "display_name": row.display_name,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "site_name": getattr(row.site, "name", None) if row.site else None,
    }


@router.get("/copy-editors", response_model=List[CopyEditorSiteMappingSchema])
async def list_copy_editor_mappings(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    文编站点映射列表。
    管理员可传 user_id 查指定用户，或不传查全部；编辑只能查自己。
    """
    q = (
        select(CopyEditorSiteMapping)
        .options(selectinload(CopyEditorSiteMapping.site))
        .order_by(CopyEditorSiteMapping.user_id, CopyEditorSiteMapping.site_id)
    )
    if current_user.role != "admin":
        q = q.where(CopyEditorSiteMapping.user_id == current_user.id)
    elif user_id is not None:
        q = q.where(CopyEditorSiteMapping.user_id == user_id)
    r = await db.execute(q)
    rows = r.scalars().all()
    return [CopyEditorSiteMappingSchema(**_copy_editor_with_site_name(x)) for x in rows]


@router.post("/copy-editors", response_model=CopyEditorSiteMappingSchema, status_code=status.HTTP_201_CREATED)
async def create_copy_editor_mapping(
    body: CopyEditorSiteMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增文编站点映射。管理员可指定 user_id，编辑只能为自己创建。"""
    uid = body.user_id if current_user.role == "admin" else current_user.id
    r = await db.execute(
        select(CopyEditorSiteMapping).where(
            CopyEditorSiteMapping.user_id == uid,
            CopyEditorSiteMapping.site_id == body.site_id,
        ).limit(1)
    )
    if r.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该用户在此站点已有映射")
    m = CopyEditorSiteMapping(
        user_id=uid,
        site_id=body.site_id,
        display_name=(body.display_name or "").strip(),
    )
    db.add(m)
    await db.commit()
    r2 = await db.execute(
        select(CopyEditorSiteMapping).where(CopyEditorSiteMapping.id == m.id).options(selectinload(CopyEditorSiteMapping.site))
    )
    m = r2.scalar_one()
    return CopyEditorSiteMappingSchema(**_copy_editor_with_site_name(m))


@router.put("/copy-editors/{mapping_id}", response_model=CopyEditorSiteMappingSchema)
async def update_copy_editor_mapping(
    mapping_id: int,
    body: CopyEditorSiteMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新文编站点映射。编辑只能改自己的。"""
    q = select(CopyEditorSiteMapping).where(CopyEditorSiteMapping.id == mapping_id).options(
        selectinload(CopyEditorSiteMapping.site)
    )
    r = await db.execute(q)
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="映射不存在")
    if current_user.role != "admin" and m.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改")
    m.display_name = (body.display_name or "").strip()
    await db.commit()
    await db.refresh(m)
    return CopyEditorSiteMappingSchema(**_copy_editor_with_site_name(m))


@router.delete("/copy-editors/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_copy_editor_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文编站点映射。编辑只能删自己的。"""
    r = await db.execute(select(CopyEditorSiteMapping).where(CopyEditorSiteMapping.id == mapping_id).limit(1))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="映射不存在")
    if current_user.role != "admin" and m.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除")
    await db.delete(m)
    await db.commit()


