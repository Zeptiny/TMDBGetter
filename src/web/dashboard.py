"""Web dashboard for monitoring TMDB data collection."""
from flask import Flask, render_template, jsonify
from sqlalchemy import func
from datetime import datetime, timedelta

from ..models import (
    get_db, ProcessingState, DailyDump, Movie, TVSeries,
    Genre, Person, ProductionCompany
)
from ..services import StateManager
from ..config import config


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
    """Dashboard home page."""
    return render_template("dashboard.html")


@app.route("/api/stats")
def stats():
    """Get overall statistics."""
    with get_db() as db:
        state_manager = StateManager(db)

        # Processing stats
        movie_stats = state_manager.get_statistics("movie")
        tv_stats = state_manager.get_statistics("tv_series")

        # Database stats
        total_movies = db.query(Movie).count()
        total_tv = db.query(TVSeries).count()
        total_genres = db.query(Genre).count()
        total_people = db.query(Person).count()
        total_companies = db.query(ProductionCompany).count()

        # Recent activity
        recent_movies = (
            db.query(Movie.title, Movie.updated_at)
            .order_by(Movie.updated_at.desc())
            .limit(10)
            .all()
        )

        recent_tv = (
            db.query(TVSeries.name, TVSeries.updated_at)
            .order_by(TVSeries.updated_at.desc())
            .limit(10)
            .all()
        )

        return jsonify({
            "processing": {
                "movies": movie_stats,
                "tv_series": tv_stats
            },
            "database": {
                "total_movies": total_movies,
                "total_tv_series": total_tv,
                "total_genres": total_genres,
                "total_people": total_people,
                "total_companies": total_companies
            },
            "recent_activity": {
                "movies": [
                    {"title": m[0], "updated_at": m[1].isoformat() if m[1] else None}
                    for m in recent_movies
                ],
                "tv_series": [
                    {"name": t[0], "updated_at": t[1].isoformat() if t[1] else None}
                    for t in recent_tv
                ]
            }
        })


@app.route("/api/processing-timeline")
def processing_timeline():
    """Get processing timeline data."""
    with get_db() as db:
        # Get processing activity over the last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)

        movie_timeline = (
            db.query(
                func.date_trunc("hour", ProcessingState.completed_at).label("hour"),
                func.count(ProcessingState.id).label("count")
            )
            .filter(
                ProcessingState.content_type == "movie",
                ProcessingState.status == "completed",
                ProcessingState.completed_at >= cutoff
            )
            .group_by("hour")
            .order_by("hour")
            .all()
        )

        tv_timeline = (
            db.query(
                func.date_trunc("hour", ProcessingState.completed_at).label("hour"),
                func.count(ProcessingState.id).label("count")
            )
            .filter(
                ProcessingState.content_type == "tv_series",
                ProcessingState.status == "completed",
                ProcessingState.completed_at >= cutoff
            )
            .group_by("hour")
            .order_by("hour")
            .all()
        )

        return jsonify({
            "movies": [
                {"hour": h[0].isoformat() if h[0] else None, "count": h[1]}
                for h in movie_timeline
            ],
            "tv_series": [
                {"hour": h[0].isoformat() if h[0] else None, "count": h[1]}
                for h in tv_timeline
            ]
        })


@app.route("/api/failed-items")
def failed_items():
    """Get failed processing items."""
    with get_db() as db:
        failed = (
            db.query(ProcessingState)
            .filter(
                ProcessingState.status == "failed",
                ProcessingState.attempts >= config.MAX_RETRIES
            )
            .order_by(ProcessingState.last_attempt_at.desc())
            .limit(50)
            .all()
        )

        return jsonify({
            "items": [
                {
                    "content_type": f.content_type,
                    "content_id": f.content_id,
                    "attempts": f.attempts,
                    "last_error": f.last_error,
                    "last_attempt_at": f.last_attempt_at.isoformat() if f.last_attempt_at else None
                }
                for f in failed
            ]
        })


@app.route("/api/dumps")
def dumps():
    """Get daily dump information."""
    with get_db() as db:
        recent_dumps = (
            db.query(DailyDump)
            .order_by(DailyDump.dump_date.desc())
            .limit(30)
            .all()
        )

        return jsonify({
            "dumps": [
                {
                    "dump_type": d.dump_type,
                    "dump_date": d.dump_date.isoformat() if d.dump_date else None,
                    "download_status": d.download_status,
                    "total_ids": d.total_ids,
                    "processed_ids": d.processed_ids,
                    "downloaded_at": d.downloaded_at.isoformat() if d.downloaded_at else None
                }
                for d in recent_dumps
            ]
        })


def run_dashboard():
    """Run the dashboard server."""
    app.run(
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        debug=False
    )
