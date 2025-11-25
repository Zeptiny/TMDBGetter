"""TV Series models."""
from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
from ..utils import utcnow


class TVSeries(Base):
    """TV Series model."""

    __tablename__ = "tv_series"

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    original_name = Column(String(500))
    original_language = Column(String(10))
    overview = Column(Text)
    tagline = Column(Text)
    status = Column(String(50), index=True)
    type = Column(String(50))
    adult = Column(Boolean, default=False)
    homepage = Column(String(500))
    in_production = Column(Boolean, default=False)
    first_air_date = Column(Date, index=True)
    last_air_date = Column(Date)
    number_of_episodes = Column(Integer, index=True)
    number_of_seasons = Column(Integer)
    popularity = Column(Float)
    vote_average = Column(Float, index=True)
    vote_count = Column(Integer, index=True)
    poster_path = Column(String(255))
    backdrop_path = Column(String(255))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, index=True)

    # Relationships
    genres = relationship("Genre", secondary="tv_series_genres", lazy="joined")
    production_companies = relationship("ProductionCompany", secondary="tv_series_production_companies", lazy="joined")
    networks = relationship("TVNetwork", secondary="tv_series_networks", lazy="joined")
    cast = relationship("TVSeriesCast", back_populates="tv_series", cascade="all, delete-orphan")
    crew = relationship("TVSeriesCrew", back_populates="tv_series", cascade="all, delete-orphan")
    creators = relationship("TVSeriesCreator", back_populates="tv_series", cascade="all, delete-orphan")
    seasons = relationship("TVSeason", back_populates="tv_series", cascade="all, delete-orphan")


class TVSeriesCast(Base):
    """TV series cast member."""

    __tablename__ = "tv_series_cast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    character = Column(String(500))
    credit_id = Column(String(50), index=True)  # Not unique - same credit may appear in re-processing
    cast_order = Column(Integer)

    # Relationships
    tv_series = relationship("TVSeries", back_populates="cast")
    person = relationship("Person", lazy="joined")


class TVSeriesCrew(Base):
    """TV series crew member."""

    __tablename__ = "tv_series_crew"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    department = Column(String(100))
    job = Column(String(100))
    credit_id = Column(String(50), index=True)  # Not unique - same credit may appear in re-processing

    # Relationships
    tv_series = relationship("TVSeries", back_populates="crew")
    person = relationship("Person", lazy="joined")


class TVSeriesCreator(Base):
    """TV series creator."""

    __tablename__ = "tv_series_creators"

    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
    credit_id = Column(String(50), index=True)  # Not unique - same credit may appear in re-processing

    # Relationships
    tv_series = relationship("TVSeries", back_populates="creators")
    person = relationship("Person", lazy="joined")


class TVSeason(Base):
    """TV season."""

    __tablename__ = "tv_seasons"

    id = Column(Integer, primary_key=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    season_number = Column(Integer, nullable=False)
    name = Column(String(500))
    overview = Column(Text)
    air_date = Column(Date)
    episode_count = Column(Integer)
    poster_path = Column(String(255))
    vote_average = Column(Float)

    # Relationships
    tv_series = relationship("TVSeries", back_populates="seasons")


class TVEpisodeInfo(Base):
    """TV episode info (last/next to air)."""

    __tablename__ = "tv_episode_info"

    id = Column(Integer, primary_key=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    episode_type = Column(SQLEnum("last_episode_to_air", "next_episode_to_air", name="episode_type"), nullable=False)
    season_number = Column(Integer)
    episode_number = Column(Integer)
    name = Column(String(500))
    overview = Column(Text)
    air_date = Column(Date)
    runtime = Column(Integer)
    vote_average = Column(Float)
    vote_count = Column(Integer)
    production_code = Column(String(50))
    still_path = Column(String(255))


class TVSeriesWatchProvider(Base):
    """TV series watch provider."""

    __tablename__ = "tv_series_watch_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("watch_providers.id", ondelete="CASCADE"), nullable=False)
    country_code = Column(String(2), nullable=False)
    type = Column(SQLEnum("flatrate", "buy", "rent", "ads", "free", name="provider_type"), nullable=False)

    # Relationships
    provider = relationship("WatchProvider", lazy="joined")


class TVSeriesTranslation(Base):
    """TV series translation."""

    __tablename__ = "tv_series_translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    iso_639_1 = Column(String(10), nullable=False)
    iso_3166_1 = Column(String(2), nullable=False)
    name = Column(String(500))
    overview = Column(Text)
    homepage = Column(String(500))
    tagline = Column(Text)


class SimilarTVSeries(Base):
    """Similar TV series."""

    __tablename__ = "similar_tv_series"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), nullable=False)
    similar_tv_series_id = Column(Integer, nullable=False)
    similarity_score = Column(Float)


class ExternalIdTVSeries(Base):
    """External IDs for TV series."""

    __tablename__ = "external_ids_tv_series"

    tv_series_id = Column(Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True)
    imdb_id = Column(String(20))
    tvdb_id = Column(Integer)
    tvrage_id = Column(Integer)
    wikidata_id = Column(String(50))
    facebook_id = Column(String(100))
    instagram_id = Column(String(100))
    twitter_id = Column(String(100))
    freebase_mid = Column(String(100))
    freebase_id = Column(String(255))
