"""Movie models."""
from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger, Date, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base
from ..utils import utcnow


class Movie(Base):
    """Movie model."""

    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    imdb_id = Column(String(20), unique=True, index=True)
    title = Column(String(500), nullable=False)
    original_title = Column(String(500))
    original_language = Column(String(10), index=True)
    overview = Column(Text)
    tagline = Column(Text)
    status = Column(String(50))
    adult = Column(Boolean, default=False)
    video = Column(Boolean, default=False)
    homepage = Column(String(500))
    budget = Column(BigInteger, default=0, index=True)
    revenue = Column(BigInteger, default=0, index=True)
    runtime = Column(Integer, index=True)
    release_date = Column(Date, index=True)
    popularity = Column(Float)
    vote_average = Column(Float, index=True)
    vote_count = Column(Integer, index=True)
    poster_path = Column(String(255))
    backdrop_path = Column(String(255))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, index=True)

    # Relationships
    genres = relationship("Genre", secondary="movie_genres", lazy="joined")
    production_companies = relationship("ProductionCompany", secondary="movie_production_companies", lazy="joined")
    cast = relationship("MovieCast", back_populates="movie", cascade="all, delete-orphan")
    crew = relationship("MovieCrew", back_populates="movie", cascade="all, delete-orphan")


class MovieCast(Base):
    """Movie cast member."""

    __tablename__ = "movie_cast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    character = Column(String(500))
    credit_id = Column(String(50), index=True)  # Not unique - same credit may appear in re-processing
    cast_order = Column(Integer)

    # Relationships
    movie = relationship("Movie", back_populates="cast")
    person = relationship("Person", lazy="joined")


class MovieCrew(Base):
    """Movie crew member."""

    __tablename__ = "movie_crew"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    department = Column(String(100))
    job = Column(String(100))
    credit_id = Column(String(50), index=True)  # Not unique - same credit may appear in re-processing

    # Relationships
    movie = relationship("Movie", back_populates="crew")
    person = relationship("Person", lazy="joined")


class MovieWatchProvider(Base):
    """Movie watch provider."""

    __tablename__ = "movie_watch_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("watch_providers.id", ondelete="CASCADE"), nullable=False)
    country_code = Column(String(2), nullable=False)
    type = Column(SQLEnum("flatrate", "buy", "rent", "ads", "free", name="provider_type"), nullable=False)

    # Relationships
    provider = relationship("WatchProvider", lazy="joined")


class MovieTranslation(Base):
    """Movie translation."""

    __tablename__ = "movie_translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    iso_639_1 = Column(String(10), nullable=False)
    iso_3166_1 = Column(String(2), nullable=False)
    name = Column(String(500))
    title = Column(String(500))
    overview = Column(Text)
    homepage = Column(String(500))
    tagline = Column(Text)


class SimilarMovie(Base):
    """Similar movies."""

    __tablename__ = "similar_movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    similar_movie_id = Column(Integer, nullable=False)
    similarity_score = Column(Float)


class ExternalIdMovie(Base):
    """External IDs for movies."""

    __tablename__ = "external_ids_movies"

    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    imdb_id = Column(String(20))
    wikidata_id = Column(String(50))
    facebook_id = Column(String(100))
    instagram_id = Column(String(100))
    twitter_id = Column(String(100))
