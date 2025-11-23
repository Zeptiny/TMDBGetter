"""Main application entry point."""
import asyncio
import sys
import signal
from argparse import ArgumentParser

from .config import config
from .utils import setup_logger
from .services import ContentProcessor
from .web.dashboard import run_dashboard


logger = setup_logger(__name__, config.LOGS_DIR / "app.log", config.LOG_LEVEL)


def parse_args():
    """Parse command line arguments."""
    parser = ArgumentParser(description="TMDB Data Collection System")
    parser.add_argument(
        "command",
        choices=["process", "dashboard", "both"],
        help="Command to run"
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Skip downloading daily dumps"
    )
    parser.add_argument(
        "--movies-only",
        action="store_true",
        help="Process only movies"
    )
    parser.add_argument(
        "--tv-only",
        action="store_true",
        help="Process only TV series"
    )
    return parser.parse_args()


async def run_processor(args):
    """Run the content processor."""
    try:
        config.validate()

        processor = ContentProcessor()

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            processor.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run processor
        await processor.run(
            download_dumps=not args.no_download,
            process_movies=not args.tv_only,
            process_tv=not args.movies_only
        )

    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        sys.exit(1)


def run_dashboard_only():
    """Run only the dashboard."""
    try:
        logger.info(f"Starting dashboard on {config.WEB_HOST}:{config.WEB_PORT}")
        run_dashboard()
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_args()

    logger.info("="*80)
    logger.info("TMDB Data Collection System Starting")
    logger.info("="*80)

    if args.command == "process":
        asyncio.run(run_processor(args))
    elif args.command == "dashboard":
        run_dashboard_only()
    elif args.command == "both":
        # Run both in separate processes
        import multiprocessing
        
        dashboard_process = multiprocessing.Process(target=run_dashboard_only)
        dashboard_process.start()
        
        try:
            asyncio.run(run_processor(args))
        finally:
            dashboard_process.terminate()
            dashboard_process.join()


if __name__ == "__main__":
    main()
