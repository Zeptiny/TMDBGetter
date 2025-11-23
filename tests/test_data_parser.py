import pytest
from datetime import datetime
from src.services.data_parser import DataParser
from src.models.movie import Movie
from src.models.tv_series import TVSeries
from src.models.common import Genre


def test_parse_movie_basic(db_session, sample_movie_data):
    """Test parsing basic movie data."""
    parser = DataParser(db_session)
    
    movie = parser.parse_movie(sample_movie_data)
    
    assert movie is not None
    assert movie.tmdb_id == 550
    assert movie.title == "Fight Club"
    assert movie.original_title == "Fight Club"
    assert movie.release_date == datetime(1999, 10, 15).date()
    assert movie.runtime == 139
    assert movie.budget == 63000000
    assert movie.revenue == 100853753
    assert movie.imdb_id == "tt0137523"


def test_parse_movie_with_genres(db_session, sample_movie_data):
    """Test parsing movie with genres."""
    parser = DataParser(db_session)
    
    movie = parser.parse_movie(sample_movie_data)
    db_session.commit()
    
    # Check that genre was created
    genre = db_session.query(Genre).filter_by(tmdb_id=18).first()
    assert genre is not None
    assert genre.name == "Drama"
    
    # Check that movie has genre
    assert len(movie.genres) == 1
    assert movie.genres[0].name == "Drama"


def test_parse_movie_with_production_companies(db_session, sample_movie_data):
    """Test parsing movie with production companies."""
    parser = DataParser(db_session)
    
    movie = parser.parse_movie(sample_movie_data)
    db_session.commit()
    
    assert len(movie.production_companies) == 1
    company = movie.production_companies[0]
    assert company.name == "Regency Enterprises"
    assert company.origin_country == "US"


def test_parse_movie_handles_missing_fields(db_session):
    """Test that parser handles missing optional fields."""
    parser = DataParser(db_session)
    
    minimal_data = {
        "id": 123,
        "title": "Test Movie",
        "original_title": "Test Movie"
    }
    
    movie = parser.parse_movie(minimal_data)
    
    assert movie is not None
    assert movie.tmdb_id == 123
    assert movie.title == "Test Movie"
    assert movie.runtime is None
    assert movie.budget is None


def test_parse_tv_series_basic(db_session, sample_tv_data):
    """Test parsing basic TV series data."""
    parser = DataParser(db_session)
    
    series = parser.parse_tv_series(sample_tv_data)
    
    assert series is not None
    assert series.tmdb_id == 1396
    assert series.name == "Breaking Bad"
    assert series.original_name == "Breaking Bad"
    assert series.number_of_episodes == 62
    assert series.number_of_seasons == 5
    assert series.status == "Ended"


def test_parse_tv_series_with_networks(db_session, sample_tv_data):
    """Test parsing TV series with networks."""
    parser = DataParser(db_session)
    
    series = parser.parse_tv_series(sample_tv_data)
    db_session.commit()
    
    assert len(series.networks) == 1
    network = series.networks[0]
    assert network.name == "AMC"
    assert network.origin_country == "US"


def test_parse_tv_series_with_seasons(db_session, sample_tv_data):
    """Test parsing TV series with seasons."""
    parser = DataParser(db_session)
    
    series = parser.parse_tv_series(sample_tv_data)
    db_session.commit()
    
    assert len(series.seasons) == 1
    season = series.seasons[0]
    assert season.season_number == 1
    assert season.episode_count == 7
    assert season.name == "Season 1"


def test_parser_updates_existing_movie(db_session, sample_movie_data):
    """Test that parser updates existing movie instead of creating duplicate."""
    parser = DataParser(db_session)
    
    # Parse movie first time
    movie1 = parser.parse_movie(sample_movie_data)
    db_session.commit()
    
    # Modify data and parse again
    sample_movie_data["title"] = "Fight Club - Updated"
    movie2 = parser.parse_movie(sample_movie_data)
    db_session.commit()
    
    # Should be same movie object
    assert movie1.tmdb_id == movie2.tmdb_id
    assert movie2.title == "Fight Club - Updated"
    
    # Should only be one movie in database
    count = db_session.query(Movie).filter_by(tmdb_id=550).count()
    assert count == 1


def test_parser_handles_invalid_dates(db_session):
    """Test that parser handles invalid date formats gracefully."""
    parser = DataParser(db_session)
    
    data = {
        "id": 999,
        "title": "Test Movie",
        "original_title": "Test Movie",
        "release_date": "invalid-date"
    }
    
    movie = parser.parse_movie(data)
    
    assert movie is not None
    assert movie.release_date is None
