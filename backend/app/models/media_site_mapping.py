from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MediaSiteMapping(Base):
    """媒体类型与站点映射"""
    __tablename__ = "media_site_mappings"

    id = Column(Integer, primary_key=True, index=True)
    media_type = Column(String(50), unique=True, nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("wordpress_sites.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    site = relationship("WordPressSite", backref="media_mappings")
