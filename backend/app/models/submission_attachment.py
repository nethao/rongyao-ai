"""
投稿附件模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SubmissionAttachment(Base):
    """投稿附件表"""
    __tablename__ = "submission_attachments"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    attachment_type = Column(String(20), nullable=False)  # image/video/word/archive/other
    oss_url = Column(String(500), nullable=False)
    oss_key = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submission = relationship("Submission", back_populates="attachments")
