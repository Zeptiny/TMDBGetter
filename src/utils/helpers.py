"""Utility helper functions."""
from datetime import datetime, date, timezone
from typing import Any, Optional


def utcnow() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def format_date_for_url(date: datetime) -> str:
    """Format date for TMDB dump URL (MM_DD_YYYY)."""
    return date.strftime("%m_%d_%Y")
