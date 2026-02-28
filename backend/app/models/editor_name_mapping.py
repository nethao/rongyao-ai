"""
采编名称映射：邮箱 -> 采编姓名（用于文章署名 责编）
"""
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class EditorNameMapping(Base):
    """采编名称映射表：邮箱或邮箱前缀 -> 采编姓名（责编）"""
    __tablename__ = "editor_name_mappings"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)  # 邮箱或前缀，如 user@qq.com 或 user
    display_name = Column(String(100), nullable=False)  # 采编姓名，用于 责编 署名
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("email", name="uq_editor_name_mapping_email"),)

    def __repr__(self):
        return f"<EditorNameMapping(email='{self.email}', display_name='{self.display_name}')>"
