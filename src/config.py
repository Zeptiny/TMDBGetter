"""Configuration management for TMDB Getter application."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    LOGS_DIR = BASE_DIR / "logs"

    # TMDB API
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    TMDB_API_BASE_URL: str = os.getenv(
        "TMDB_API_BASE_URL", "https://api.themoviedb.org/3"
    )
    TMDB_DUMP_BASE_URL: str = os.getenv(
        "TMDB_DUMP_BASE_URL", "https://files.tmdb.org/p/exports"
    )

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "tmdb")
    DB_USER: str = os.getenv("DB_USER", "tmdb_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    @property
    def DATABASE_URL(self) -> str:
        """Build database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Application settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "29"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))
    CHECKPOINT_INTERVAL: int = int(os.getenv("CHECKPOINT_INTERVAL", "100"))

    # Web Dashboard
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))

    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.TMDB_API_KEY:
            raise ValueError("TMDB_API_KEY is required")
        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is required")
        return True


config = Config()
