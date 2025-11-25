"""State tracking models."""
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Enum as SQLEnum
from datetime import datetime
from enum import Enum
from .base import Base
from ..utils import utcnow


class ProcessingStatus(str, Enum):
    """Processing status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadStatus(str, Enum):
    """Download status enum."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingState(Base):
    """Track processing state for each content ID."""

    __tablename__ = "processing_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(SQLEnum("movie", "tv_series", name="content_type"), nullable=False)
    content_id = Column(Integer, nullable=False)
    status = Column(
        SQLEnum("pending", "processing", "completed", "failed", name="processing_status"),
        nullable=False,
        default="pending"
    )
    attempts = Column(Integer, default=0)
    last_error = Column(Text)
    last_attempt_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)


class DailyDump(Base):
    """Track daily dump downloads."""

    __tablename__ = "daily_dumps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dump_type = Column(SQLEnum("movie", "tv_series", name="dump_type"), nullable=False)
    dump_date = Column(Date, nullable=False)
    file_url = Column(String(500))
    download_status = Column(
        SQLEnum("pending", "downloading", "completed", "failed", name="download_status"),
        nullable=False,
        default="pending"
    )
    total_ids = Column(Integer, default=0)
    processed_ids = Column(Integer, default=0)
    downloaded_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
