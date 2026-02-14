"""
投稿模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Submission(Base):
    """投稿表"""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    email_subject = Column(String(255))
    email_from = Column(String(255))
    email_date = Column(DateTime(timezone=True))
    original_content = Column(Text, nullable=False)
    original_html = Column(Text)  # 原始HTML（保留公众号排版）
    doc_file_path = Column(String(500))
    docx_file_path = Column(String(500))
    status = Column(String(20), nullable=False, default='pending')  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text)
    
    # 邮件解析元数据
    cooperation_type = Column(String(20))  # 'free' 或 'partner'
    media_type = Column(String(20))  # 'rongyao', 'shidai', 'zhengxian', 'zhengqi', 'toutiao'
    source_unit = Column(String(255))  # 来稿单位
    target_site_id = Column(Integer)  # 目标WordPress站点ID
    content_source = Column(String(20))  # 'weixin', 'meipian', 'doc', 'docx', 'text'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    images = relationship("SubmissionImage", back_populates="submission", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="submission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Submission(id={self.id}, status='{self.status}')>"


class SubmissionImage(Base):
    """投稿图片表"""
    __tablename__ = "submission_images"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    oss_url = Column(String(500), nullable=False)
    oss_key = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    compressed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    submission = relationship("Submission", back_populates="images")

    def __repr__(self):
        return f"<SubmissionImage(id={self.id}, submission_id={self.submission_id})>"
