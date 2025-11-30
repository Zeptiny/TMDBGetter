"""Content processor orchestrator."""
import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ..config import config
from ..utils import setup_logger
from ..models import get_db, init_db
from .api_client import TMDBAPIClient, TMDBAPIError
from .data_parser import DataParser
from .state_manager import StateManager
from .download_manager import DownloadManager


logger = setup_logger(__name__, config.LOGS_DIR / "processor.log", config.LOG_LEVEL)


class ContentProcessor:
    """Orchestrator for content processing."""

    def __init__(self):
        """Initialize content processor."""
        self.download_manager = DownloadManager()
        self.running = True
        self.checkpoint_counter = 0

    async def download_daily_dumps(self, date: Optional[datetime] = None):
        """Download daily dumps for movies and TV series."""
        if date is None:
            date = datetime.now()

        logger.info(f"Downloading daily dumps for {date.date()}")

        with get_db() as db:
            # Download movie IDs
            try:
                movie_ids = await self.download_manager.download_dump("movie", date, db)
                if movie_ids:
                    self.download_manager.load_ids_to_state("movie", movie_ids, db)
            except Exception as e:
                logger.error(f"Failed to download movie dump: {str(e)}")

            # Download TV series IDs
            try:
                tv_ids = await self.download_manager.download_dump("tv_series", date, db)
                if tv_ids:
                    self.download_manager.load_ids_to_state("tv_series", tv_ids, db)
            except Exception as e:
                logger.error(f"Failed to download TV series dump: {str(e)}")

    async def process_content(self, content_type: str, batch_size: int = 100):
        """
        Process pending content.

        Args:
            content_type: Type of content ('movie' or 'tv_series')
            batch_size: Number of items to process in each batch
        """
        logger.info(f"Starting {content_type} processing")

        async with TMDBAPIClient() as api_client:
            while self.running:
                # Get pending IDs
                with get_db() as db:
                    state_manager = StateManager(db)

                    # Reset stuck processing states
                    state_manager.reset_stuck_processing(content_type)

                    # Get batch of pending IDs
                    pending = state_manager.get_pending_ids(content_type, limit=batch_size)

                    if not pending:
                        logger.info(f"No more pending {content_type} IDs")
                        break

                    logger.info(f"Processing batch of {len(pending)} {content_type} IDs")

                # Process batch
                tasks = [
                    self._process_single_content(
                        api_client, content_type, state_id, content_id
                    )
                    for state_id, content_id in pending
                ]

                await asyncio.gather(*tasks, return_exceptions=True)

                # Log statistics
                with get_db() as db:
                    state_manager = StateManager(db)
                    stats = state_manager.get_statistics(content_type)
                    logger.info(
                        f"{content_type.title()} progress: "
                        f"{stats['completed']}/{stats['total']} "
                        f"({stats['completion_rate']:.2f}%) | "
                        f"Failed: {stats['failed']} | "
                        f"Pending: {stats['pending']}"
                    )

        logger.info(f"Completed {content_type} processing")

    async def _process_single_content(
        self,
        api_client: TMDBAPIClient,
        content_type: str,
        state_id: int,
        content_id: int
    ):
        """Process a single content item."""
        # Mark as processing (run in thread to not block event loop)
        await asyncio.to_thread(self._mark_processing_sync, state_id)

        try:
            # Fetch data from API
            if content_type == "movie":
                data = await api_client.get_movie_details(content_id)
            else:
                data = await api_client.get_tv_series_details(content_id)

            # Parse and save to database (run in thread to not block event loop)
            await asyncio.to_thread(self._save_content_sync, content_type, data, state_id)

            self.checkpoint_counter += 1
            if self.checkpoint_counter % config.CHECKPOINT_INTERVAL == 0:
                logger.info(f"Checkpoint: Processed {self.checkpoint_counter} items")

        except TMDBAPIError as e:
            if e.status_code == 404:
                # Content doesn't exist (deleted from TMDB), mark as completed to skip
                logger.warning(f"{content_type} {content_id} not found on TMDB (404)")
                await asyncio.to_thread(self._mark_completed_sync, state_id)
            else:
                error_msg = str(e)
                logger.error(f"Failed to process {content_type} {content_id}: {error_msg}")
                await asyncio.to_thread(self._mark_failed_sync, state_id, error_msg)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to process {content_type} {content_id}: {error_msg}")
            await asyncio.to_thread(self._mark_failed_sync, state_id, error_msg)

    def _mark_processing_sync(self, state_id: int):
        """Synchronous helper to mark processing state."""
        with get_db() as db:
            state_manager = StateManager(db)
            state_manager.mark_processing(state_id)

    def _save_content_sync(self, content_type: str, data: dict, state_id: int):
        """Synchronous helper to save content and mark completed."""
        with get_db() as db:
            parser = DataParser(db)
            if content_type == "movie":
                parser.parse_movie(data)
            else:
                parser.parse_tv_series(data)
            db.commit()
            
            state_manager = StateManager(db)
            state_manager.mark_completed(state_id)

    def _mark_completed_sync(self, state_id: int):
        """Synchronous helper to mark completed state."""
        with get_db() as db:
            state_manager = StateManager(db)
            state_manager.mark_completed(state_id)

    def _mark_failed_sync(self, state_id: int, error_msg: str):
        """Synchronous helper to mark failed state."""
        with get_db() as db:
            state_manager = StateManager(db)
            state_manager.mark_failed(state_id, error_msg)

    async def check_and_schedule_updates(self):
        """Check for content that needs updating and schedule them."""
        logger.info("Checking for content that needs updating")

        with get_db() as db:
            state_manager = StateManager(db)

            # Check movies
            movie_ids = state_manager.check_for_updates("movie")
            if movie_ids:
                logger.info(f"Found {len(movie_ids)} movies that need updating")
                state_manager.schedule_updates("movie", movie_ids)

            # Check TV series
            tv_ids = state_manager.check_for_updates("tv_series")
            if tv_ids:
                logger.info(f"Found {len(tv_ids)} TV series that need updating")
                state_manager.schedule_updates("tv_series", tv_ids)

    async def run(self, download_dumps: bool = True, process_movies: bool = True, process_tv: bool = True):
        """
        Run the full processing pipeline continuously.

        The processor will:
        1. Download daily dumps and process all pending content
        2. Once complete, sleep and periodically check for:
           - New daily dumps (every DUMP_CHECK_INTERVAL seconds)
           - Content that needs updating (every UPDATE_CHECK_INTERVAL seconds)
        3. Process any new pending content
        4. Repeat

        Args:
            download_dumps: Whether to download daily dumps
            process_movies: Whether to process movies
            process_tv: Whether to process TV series
        """
        try:
            # Initialize database
            init_db()

            logger.info("Starting continuous processing mode")
            
            last_dump_check = 0
            last_update_check = 0

            while self.running:
                current_time = asyncio.get_event_loop().time()
                has_work = False

                # Check if it's time to download new dumps
                if download_dumps and (current_time - last_dump_check) >= config.DUMP_CHECK_INTERVAL:
                    logger.info("Checking for new daily dumps...")
                    await self.download_daily_dumps()
                    last_dump_check = current_time
                    has_work = True

                # Check if it's time to look for updates
                if (current_time - last_update_check) >= config.UPDATE_CHECK_INTERVAL:
                    await self.check_and_schedule_updates()
                    last_update_check = current_time

                # Check if there's pending work
                with get_db() as db:
                    state_manager = StateManager(db)
                    movie_stats = state_manager.get_statistics("movie") if process_movies else {"pending": 0}
                    tv_stats = state_manager.get_statistics("tv_series") if process_tv else {"pending": 0}
                    pending_count = movie_stats.get("pending", 0) + tv_stats.get("pending", 0)

                if pending_count > 0:
                    has_work = True
                    logger.info(f"Found {pending_count} pending items to process")

                    # Process content in parallel
                    tasks = []
                    if process_movies and movie_stats.get("pending", 0) > 0:
                        tasks.append(self.process_content("movie"))
                    if process_tv and tv_stats.get("pending", 0) > 0:
                        tasks.append(self.process_content("tv_series"))

                    if tasks:
                        await asyncio.gather(*tasks)

                    logger.info("Processing batch completed")

                if not has_work:
                    # No work to do, sleep before next check
                    sleep_time = min(config.DUMP_CHECK_INTERVAL, config.UPDATE_CHECK_INTERVAL)
                    logger.info(f"No pending work. Sleeping for {sleep_time // 60} minutes...")
                    
                    # Sleep in smaller intervals to allow graceful shutdown
                    for _ in range(sleep_time // 60):
                        if not self.running:
                            break
                        await asyncio.sleep(60)
                    
                    # Sleep remaining seconds
                    if self.running:
                        await asyncio.sleep(sleep_time % 60)

            logger.info("Processor stopped")

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down gracefully...")
            self.running = False
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            raise

    def stop(self):
        """Stop the processor gracefully."""
        self.running = False
        logger.info("Processor stop requested")
