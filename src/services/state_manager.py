"""State manager for tracking processing state."""
from datetime import datetime, timezone
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import ProcessingState, DailyDump
from ..utils import setup_logger, utcnow
from ..config import config


logger = setup_logger(__name__, config.LOGS_DIR / "state.log", config.LOG_LEVEL)


class StateManager:
    """Manager for processing state."""

    def __init__(self, db: Session):
        """Initialize state manager."""
        self.db = db

    def get_pending_ids(
        self,
        content_type: str,
        limit: int = 1000
    ) -> List[Tuple[int, int]]:
        """
        Get pending or failed (with retries left) content IDs.

        Args:
            content_type: Type of content ('movie' or 'tv_series')
            limit: Maximum number of IDs to return

        Returns:
            List of (state_id, content_id) tuples
        """
        states = (
            self.db.query(ProcessingState.id, ProcessingState.content_id)
            .filter(
                and_(
                    ProcessingState.content_type == content_type,
                    ProcessingState.status.in_(["pending", "failed"]),
                    ProcessingState.attempts < config.MAX_RETRIES
                )
            )
            .limit(limit)
            .all()
        )
        return states

    def mark_processing(self, state_id: int):
        """Mark a state as processing."""
        state = self.db.query(ProcessingState).filter_by(id=state_id).first()
        if state:
            state.status = "processing"
            state.attempts += 1
            state.last_attempt_at = utcnow()
            self.db.commit()

    def mark_completed(self, state_id: int):
        """Mark a state as completed."""
        state = self.db.query(ProcessingState).filter_by(id=state_id).first()
        if state:
            state.status = "completed"
            state.completed_at = utcnow()
            state.last_error = None
            self.db.commit()

    def mark_failed(self, state_id: int, error: str):
        """Mark a state as failed."""
        state = self.db.query(ProcessingState).filter_by(id=state_id).first()
        if state:
            state.status = "failed"
            state.last_error = error[:1000]  # Limit error length
            state.last_attempt_at = utcnow()
            self.db.commit()

    def get_statistics(self, content_type: str) -> dict:
        """Get processing statistics."""
        total = self.db.query(ProcessingState).filter_by(content_type=content_type).count()
        completed = self.db.query(ProcessingState).filter_by(
            content_type=content_type,
            status="completed"
        ).count()
        failed = self.db.query(ProcessingState).filter(
            and_(
                ProcessingState.content_type == content_type,
                ProcessingState.status == "failed",
                ProcessingState.attempts >= config.MAX_RETRIES
            )
        ).count()
        pending = total - completed - failed

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total > 0 else 0
        }

    def reset_stuck_processing(self, content_type: str, hours: int = 1):
        """Reset states that have been stuck in 'processing' for too long."""
        cutoff = utcnow().timestamp() - (hours * 3600)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

        updated = (
            self.db.query(ProcessingState)
            .filter(
                and_(
                    ProcessingState.content_type == content_type,
                    ProcessingState.status == "processing",
                    ProcessingState.last_attempt_at < cutoff_dt
                )
            )
            .update({"status": "pending"})
        )

        self.db.commit()
        if updated > 0:
            logger.warning(f"Reset {updated} stuck {content_type} processing states")
        return updated

    def check_for_updates(self, content_type: str) -> List[int]:
        """
        Check for content that needs updating (completed but old).
        Returns IDs that haven't been updated in the last 30 days.
        """
        cutoff = utcnow().timestamp() - (30 * 24 * 3600)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

        # Get completed IDs that need updating
        if content_type == "movie":
            from ..models import Movie
            ids = [
                row[0] for row in self.db.query(Movie.id)
                .filter(Movie.updated_at < cutoff_dt)
                .all()
            ]
        else:
            from ..models import TVSeries
            ids = [
                row[0] for row in self.db.query(TVSeries.id)
                .filter(TVSeries.updated_at < cutoff_dt)
                .all()
            ]

        return ids

    def schedule_updates(self, content_type: str, content_ids: List[int]):
        """Schedule content IDs for update by resetting their state."""
        if not content_ids:
            return

        logger.info(f"Scheduling {len(content_ids)} {content_type} IDs for update")

        # Reset their state to pending
        self.db.query(ProcessingState).filter(
            and_(
                ProcessingState.content_type == content_type,
                ProcessingState.content_id.in_(content_ids)
            )
        ).update(
            {
                "status": "pending",
                "attempts": 0,
                "last_error": None
            },
            synchronize_session=False
        )

        self.db.commit()
