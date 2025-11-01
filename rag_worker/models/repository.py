"""
저장소 모델 정의 (rag_worker용)
"""

import uuid
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func

from .database import Base
from .types import GUID


class Repository(Base):
    """저장소 모델"""
    __tablename__ = "repositories"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    url = Column(String(255), nullable=False)
    owner_id = Column(GUID(), nullable=False)  # ForeignKey removed for rag_worker
    stars = Column(Integer, default=0)
    language = Column(String(50))
    status = Column(String(20), default="pending")  # pending, syncing, active, error
    vectordb_status = Column(String(20), default="pending")  # pending, syncing, active, error
    error_message = Column(Text, nullable=True)  # 에러 발생 시 상세 메시지
    collections_count = Column(Integer, default=0)
    file_count = Column(Integer, default=0)  # 파싱된 파일 개수
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync = Column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name}, owner_id={self.owner_id})>"
