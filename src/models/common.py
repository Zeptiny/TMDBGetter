"""Common shared models (genres, companies, languages, etc.)."""
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from .base import Base


# Association tables
movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

tv_series_genres = Table(
    "tv_series_genres",
    Base.metadata,
    Column("tv_series_id", Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

movie_production_companies = Table(
    "movie_production_companies",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", Integer, ForeignKey("production_companies.id", ondelete="CASCADE"), primary_key=True),
)

tv_series_production_companies = Table(
    "tv_series_production_companies",
    Base.metadata,
    Column("tv_series_id", Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", Integer, ForeignKey("production_companies.id", ondelete="CASCADE"), primary_key=True),
)

movie_production_countries = Table(
    "movie_production_countries",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("country_code", String(2), ForeignKey("production_countries.iso_3166_1", ondelete="CASCADE"), primary_key=True),
)

tv_series_production_countries = Table(
    "tv_series_production_countries",
    Base.metadata,
    Column("tv_series_id", Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True),
    Column("country_code", String(2), ForeignKey("production_countries.iso_3166_1", ondelete="CASCADE"), primary_key=True),
)

movie_spoken_languages = Table(
    "movie_spoken_languages",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("language_code", String(10), ForeignKey("spoken_languages.iso_639_1", ondelete="CASCADE"), primary_key=True),
)

tv_series_spoken_languages = Table(
    "tv_series_spoken_languages",
    Base.metadata,
    Column("tv_series_id", Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True),
    Column("language_code", String(10), ForeignKey("spoken_languages.iso_639_1", ondelete="CASCADE"), primary_key=True),
)

movie_keywords = Table(
    "movie_keywords",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
)

tv_series_keywords = Table(
    "tv_series_keywords",
    Base.metadata,
    Column("tv_series_id", Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
)

tv_series_networks = Table(
    "tv_series_networks",
    Base.metadata,
    Column("tv_series_id", Integer, ForeignKey("tv_series.id", ondelete="CASCADE"), primary_key=True),
    Column("network_id", Integer, ForeignKey("tv_networks.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base):
    """Genre model."""

    __tablename__ = "genres"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)


class ProductionCompany(Base):
    """Production company model."""

    __tablename__ = "production_companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    logo_path = Column(String(255))
    origin_country = Column(String(2))


class ProductionCountry(Base):
    """Production country model."""

    __tablename__ = "production_countries"

    iso_3166_1 = Column(String(2), primary_key=True)
    name = Column(String(100), nullable=False)


class SpokenLanguage(Base):
    """Spoken language model."""

    __tablename__ = "spoken_languages"

    iso_639_1 = Column(String(10), primary_key=True)
    english_name = Column(String(100))
    name = Column(String(100))


class Keyword(Base):
    """Keyword model."""

    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)


class WatchProvider(Base):
    """Watch provider model."""

    __tablename__ = "watch_providers"

    id = Column(Integer, primary_key=True)
    provider_name = Column(String(255), nullable=False)
    logo_path = Column(String(255))
    display_priority = Column(Integer)


class TVNetwork(Base):
    """TV network model."""

    __tablename__ = "tv_networks"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    logo_path = Column(String(255))
    origin_country = Column(String(2))
