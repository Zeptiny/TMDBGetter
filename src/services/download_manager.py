"""Download manager for TMDB daily dumps."""
import gzip
import json
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..config import config
from ..utils import setup_logger, format_date_for_url, utcnow
from ..models import DailyDump, ProcessingState


logger = setup_logger(__name__, config.LOGS_DIR / "download.log", config.LOG_LEVEL)


class DownloadManager:
    """Manager for downloading and processing TMDB daily dumps."""

    def __init__(self):
        """Initialize download manager."""
        self.base_url = config.TMDB_DUMP_BASE_URL
        self.temp_dir = config.BASE_DIR / "temp"
        self.temp_dir.mkdir(exist_ok=True)

    def _build_dump_url(self, dump_type: str, date: datetime) -> str:
        """Build URL for daily dump file."""
        date_str = format_date_for_url(date)
        if dump_type == "movie":
            filename = f"movie_ids_{date_str}.json.gz"
        elif dump_type == "tv_series":
            filename = f"tv_series_ids_{date_str}.json.gz"
        else:
            raise ValueError(f"Invalid dump type: {dump_type}")

        return f"{self.base_url}/{filename}"

    async def download_dump(
        self,
        dump_type: str,
        date: datetime,
        db: Session
    ) -> List[int]:
        """
        Download and parse daily dump file.

        Args:
            dump_type: Type of dump ('movie' or 'tv_series')
            date: Date of dump to download
            db: Database session

        Returns:
            List of content IDs
        """
        url = self._build_dump_url(dump_type, date)
        logger.info(f"Downloading {dump_type} dump from {url}")

        # Check if already downloaded
        existing = db.query(DailyDump).filter_by(
            dump_type=dump_type,
            dump_date=date.date()
        ).first()

        if existing and existing.download_status == "completed":
            logger.info(f"Dump already downloaded: {dump_type} {date.date()}")
            return []

        # Create or update dump record
        if not existing:
            existing = DailyDump(
                dump_type=dump_type,
                dump_date=date.date(),
                file_url=url,
                download_status="downloading"
            )
            db.add(existing)
        else:
            existing.download_status = "downloading"
        db.commit()

        try:
            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=300) as response:
                    if response.status == 404:
                        logger.error(f"Dump file not found: {url}")
                        existing.download_status = "failed"
                        db.commit()
                        return []

                    response.raise_for_status()

                    # Save to temp file
                    temp_file = self.temp_dir / f"{dump_type}_{date.strftime('%Y%m%d')}.json.gz"
                    with open(temp_file, "wb") as f:
                        f.write(await response.read())

            # Parse file
            ids = self._parse_dump_file(temp_file)
            logger.info(f"Found {len(ids)} IDs in {dump_type} dump")

            # Update dump record
            existing.download_status = "completed"
            existing.total_ids = len(ids)
            existing.downloaded_at = utcnow()
            db.commit()

            # Clean up temp file
            temp_file.unlink()

            return ids

        except Exception as e:
            logger.error(f"Failed to download dump: {str(e)}")
            existing.download_status = "failed"
            db.commit()
            raise

    def _parse_dump_file(self, file_path: Path) -> List[int]:
        """
        Parse gzipped dump file and extract IDs.

        Each line is a separate JSON object with format:
        {"id": 123, "original_title": "...", "popularity": 1.23}
        """
        ids = []
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    ids.append(data["id"])
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse line: {str(e)}")
                    continue
        return ids

    def load_ids_to_state(
        self,
        content_type: str,
        ids: List[int],
        db: Session
    ):
        """
        Load content IDs into processing state table.

        Args:
            content_type: Type of content ('movie' or 'tv_series')
            ids: List of content IDs
            db: Database session
        """
        logger.info(f"Loading {len(ids)} {content_type} IDs to processing state")

        # Get existing IDs
        existing_ids = set(
            row[0] for row in db.query(ProcessingState.content_id)
            .filter_by(content_type=content_type)
            .all()
        )

        # Add new IDs
        new_ids = [id for id in ids if id not in existing_ids]
        if new_ids:
            for content_id in new_ids:
                state = ProcessingState(
                    content_type=content_type,
                    content_id=content_id,
                    status="pending"
                )
                db.add(state)

            db.commit()
            logger.info(f"Added {len(new_ids)} new {content_type} IDs to processing queue")
        else:
            logger.info(f"No new {content_type} IDs to add")
