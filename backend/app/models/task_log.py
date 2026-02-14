"""
任务日志模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class TaskLog(Base):
    """任务日志表"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False, index=True)  # 'fetch_email', 'ai_transform', 'cleanup'
    task_id = Column(String(100))
    status = Column(String(20), nullable=False)  # 'started', 'success', 'failed'
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<TaskLog(id={self.id}, type='{self.task_type}', status='{self.status}')>"
