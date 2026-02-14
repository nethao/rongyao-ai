"""
WordPress站点模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class WordPressSite(Base):
    """WordPress站点表"""
    __tablename__ = "wordpress_sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(255), nullable=False)
    api_username = Column(String(100))
    api_password_encrypted = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WordPressSite(id={self.id}, name='{self.name}', url='{self.url}', active={self.active})>"
