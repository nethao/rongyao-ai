"""
草稿模型
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Draft(Base):
    """草稿表"""
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    
    # 占位符协议字段
    original_content_md = Column(Text)  # 原始Markdown（带[[IMG_x]]占位符）
    ai_content_md = Column(Text)  # AI改写后的Markdown（带[[IMG_x]]占位符）
    media_map = Column(JSON)  # {"[[IMG_1]]": "https://oss...", "[[IMG_2]]": "..."}
    
    # 旧字段（保留作为备份）
    current_content = Column(Text, nullable=False)
    
    current_version = Column(Integer, default=1)
    status = Column(String(20), nullable=False, default='draft')  # 'draft', 'published'
    published_at = Column(DateTime(timezone=True))
    published_to_site_id = Column(Integer, ForeignKey("wordpress_sites.id"))
    wordpress_post_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    submission = relationship("Submission", back_populates="drafts")
    versions = relationship("DraftVersion", back_populates="draft", cascade="all, delete-orphan")
    published_site = relationship("WordPressSite")

    def __repr__(self):
        return f"<Draft(id={self.id}, submission_id={self.submission_id}, status='{self.status}')>"


class DraftVersion(Base):
    """草稿版本表"""
    __tablename__ = "draft_versions"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_md = Column(Text)  # Markdown版本（带占位符）
    media_map = Column(JSON)  # 该版本的media_map快照
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    draft = relationship("Draft", back_populates="versions")
    creator = relationship("User")

    def __repr__(self):
        return f"<DraftVersion(id={self.id}, draft_id={self.draft_id}, version={self.version_number})>"
