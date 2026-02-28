"""
重复稿件记录模型（C 方案：不改动 submissions 表）
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class DuplicateLog(Base):
    """重复稿件记录表"""
    __tablename__ = "duplicate_logs"

    id = Column(Integer, primary_key=True, index=True)
    email_subject = Column(String(255), nullable=False)
    email_from = Column(String(255))
    email_date = Column(DateTime(timezone=True))
    cooperation_type = Column(String(20))
    media_type = Column(String(20))
    source_unit = Column(String(255))
    title = Column(String(500))
    duplicate_type = Column(String(20), nullable=False)  # 'skipped' | 'superseded'
    effective_submission_id = Column(Integer, ForeignKey("submissions.id"))
    superseded_submission_id = Column(Integer, ForeignKey("submissions.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
