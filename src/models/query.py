"""Saved query models."""
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .base import Base


class SavedQuery(Base):
    """Saved SQL query model."""

    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    query_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
