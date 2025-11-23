"""Person model."""
from sqlalchemy import Column, Integer, String, Boolean, Float
from .base import Base


class Person(Base):
    """Person model (actors, crew members, etc.)."""

    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    original_name = Column(String(255))
    gender = Column(Integer)  # 0=not specified, 1=female, 2=male, 3=non-binary
    adult = Column(Boolean, default=False)
    known_for_department = Column(String(100))
    popularity = Column(Float)
    profile_path = Column(String(255))
