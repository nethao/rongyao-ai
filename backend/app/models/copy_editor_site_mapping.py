"""
文编/编辑人员站点名称映射：用户在不同站点下的署名（用于文章署名 文编）
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class CopyEditorSiteMapping(Base):
    """文编站点映射：user_id + site_id -> 该站点下的文编署名"""
    __tablename__ = "copy_editor_site_mappings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("wordpress_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)  # 在该站点下的文编署名
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_id", "site_id", name="uq_copy_editor_site_user_site"),)

    user = relationship("User", backref="copy_editor_site_mappings", foreign_keys=[user_id])
    site = relationship("WordPressSite", backref="copy_editor_mappings", foreign_keys=[site_id])

    def __repr__(self):
        return f"<CopyEditorSiteMapping(user_id={self.user_id}, site_id={self.site_id}, display_name='{self.display_name}')>"
