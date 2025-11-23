import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_movie_data():
    """Sample movie data for testing."""
    return {
        "id": 550,
        "title": "Fight Club",
        "original_title": "Fight Club",
        "overview": "A ticking-time-bomb insomniac...",
        "release_date": "1999-10-15",
        "runtime": 139,
        "budget": 63000000,
        "revenue": 100853753,
        "popularity": 61.416,
        "vote_average": 8.433,
        "vote_count": 26280,
        "adult": False,
        "original_language": "en",
        "status": "Released",
        "tagline": "Mischief. Mayhem. Soap.",
        "homepage": "http://www.foxmovies.com/movies/fight-club",
        "imdb_id": "tt0137523",
        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "backdrop_path": "/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
        "genres": [
            {"id": 18, "name": "Drama"}
        ],
        "production_companies": [
            {
                "id": 508,
                "name": "Regency Enterprises",
                "logo_path": "/7PzJdsLGlR7oW4J0J5Xcd0pHGRg.png",
                "origin_country": "US"
            }
        ],
        "production_countries": [
            {"iso_3166_1": "US", "name": "United States of America"}
        ],
        "spoken_languages": [
            {"iso_639_1": "en", "name": "English"}
        ],
        "keywords": {
            "keywords": [
                {"id": 825, "name": "support group"}
            ]
        }
    }


@pytest.fixture
def sample_tv_data():
    """Sample TV series data for testing."""
    return {
        "id": 1396,
        "name": "Breaking Bad",
        "original_name": "Breaking Bad",
        "overview": "A high school chemistry teacher...",
        "first_air_date": "2008-01-20",
        "last_air_date": "2013-09-29",
        "number_of_episodes": 62,
        "number_of_seasons": 5,
        "episode_run_time": [45, 47],
        "popularity": 396.883,
        "vote_average": 8.891,
        "vote_count": 12701,
        "adult": False,
        "original_language": "en",
        "status": "Ended",
        "type": "Scripted",
        "tagline": "",
        "homepage": "http://www.amc.com/shows/breaking-bad",
        "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
        "backdrop_path": "/tsRy63Mu5cu8etL1X7ZLyf7UP1M.jpg",
        "genres": [
            {"id": 18, "name": "Drama"},
            {"id": 80, "name": "Crime"}
        ],
        "production_companies": [
            {
                "id": 11073,
                "name": "Sony Pictures Television Studios",
                "logo_path": "/aCbASRcI1MI7DXjPbSW9Fcv9uGR.png",
                "origin_country": "US"
            }
        ],
        "created_by": [
            {
                "id": 66633,
                "name": "Vince Gilligan",
                "gender": 2,
                "profile_path": "/wSTvJGz7QbJf1HK2Mv1Cev6W9TV.jpg"
            }
        ],
        "networks": [
            {
                "id": 174,
                "name": "AMC",
                "logo_path": "/pmvRmATOCaDykE6JrVoeYxlFHw3.png",
                "origin_country": "US"
            }
        ],
        "seasons": [
            {
                "id": 3572,
                "name": "Season 1",
                "overview": "",
                "season_number": 1,
                "episode_count": 7,
                "air_date": "2008-01-20",
                "poster_path": "/1BP4xYv9ZG4ZVHkL7ocOziBbSYH.jpg"
            }
        ]
    }
