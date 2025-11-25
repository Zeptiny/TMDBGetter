"""Web dashboard for monitoring TMDB data collection."""
import subprocess
from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from sqlalchemy import func, text, inspect
from datetime import datetime, timedelta, timezone

from ..models import (
    get_db, ProcessingState, DailyDump, Movie, TVSeries,
    Genre, Person, ProductionCompany, SavedQuery
)
from ..services import StateManager
from ..config import config
from ..utils import utcnow


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
    """Dashboard home page."""
    return render_template("index.html")


@app.route("/movies")
def movies_page():
    """Movies management page."""
    return render_template("movies.html")


@app.route("/tv")
def tv_page():
    """TV Series management page."""
    return render_template("tv.html")


@app.route("/failed")
def failed_page():
    """Failed items management page."""
    return render_template("failed.html")


@app.route("/analysis")
def analysis_page():
    """Data analysis page."""
    return render_template("analysis.html")


@app.route("/system")
def system_page():
    """System status page."""
    return render_template("system.html")


@app.route("/query")
def query_page():
    """SQL Lab page."""
    return render_template("query.html")


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
        total_people = db.query(Person).count()
        total_companies = db.query(ProductionCompany).count()

        # Daily Dumps
        recent_dumps = (
            db.query(DailyDump)
            .order_by(DailyDump.dump_date.desc())
            .limit(5)
            .all()
        )

        dumps_data = [
            {
                "type": d.dump_type,
                "date": d.dump_date.isoformat() if d.dump_date else None,
                "total": d.total_ids,
                "processed": d.processed_ids,
                "status": d.download_status
            }
            for d in recent_dumps
        ]

        # Recent activity
        recent_movies = (
            db.query(Movie.title, Movie.updated_at)
            .order_by(Movie.updated_at.desc())
            .limit(5)
            .all()
        )

        recent_tv = (
            db.query(TVSeries.name, TVSeries.updated_at)
            .order_by(TVSeries.updated_at.desc())
            .limit(5)
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
                "total_people": total_people,
                "total_companies": total_companies
            },
            "daily_dumps": dumps_data,
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
        cutoff = utcnow() - timedelta(hours=24)

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


@app.route("/api/failed")
def api_failed():
    """Paginated failed items listing and search."""
    q = request.args.get('q')
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 20))
    except Exception:
        per_page = 20

    offset = (page - 1) * per_page

    with get_db() as db:
        base = db.query(ProcessingState).filter(ProcessingState.status == 'failed')
        
        if q:
            if q.isdigit():
                base = base.filter(ProcessingState.content_id == int(q))
            else:
                like = f"%{q}%"
                base = base.filter(ProcessingState.last_error.ilike(like))

        total = base.count()
        rows = base.order_by(ProcessingState.last_attempt_at.desc()).offset(offset).limit(per_page).all()

        items = [
            {
                "id": r.content_id,
                "type": r.content_type,
                "attempts": r.attempts,
                "last_error": r.last_error,
                "last_attempt_at": r.last_attempt_at.isoformat() if r.last_attempt_at else None
            }
            for r in rows
        ]

        return jsonify({
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })


@app.route("/api/failed/retry", methods=["POST"])
def api_failed_retry_single():
    """Retry a single failed item."""
    data = request.get_json()
    content_id = data.get("content_id")
    content_type = data.get("content_type")
    
    if not content_id or not content_type:
        return jsonify({"error": "content_id and content_type are required"}), 400
    
    with get_db() as db:
        try:
            state = db.query(ProcessingState).filter(
                ProcessingState.content_id == content_id,
                ProcessingState.content_type == content_type,
                ProcessingState.status == "failed"
            ).first()
            
            if not state:
                return jsonify({"error": "Failed item not found"}), 404
            
            state.status = "pending"
            state.attempts = 0
            state.last_error = None
            db.commit()
            
            return jsonify({
                "message": f"Item {content_id} reset to pending for retry",
                "reset_count": 1
            })
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 400


@app.route("/api/failed/retry-all", methods=["POST"])
def api_failed_retry_all():
    """Retry all failed items."""
    data = request.get_json() or {}
    content_type = data.get("content_type")  # Optional filter
    
    with get_db() as db:
        try:
            state_manager = StateManager(db)
            reset_count = state_manager.retry_all_failed(content_type)
            
            return jsonify({
                "message": f"Reset {reset_count} failed items to pending for retry",
                "reset_count": reset_count
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400


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


@app.route("/api/movies")
def api_movies():
    """Paginated movie listing and search."""
    q = request.args.get('q')
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 20))
    except Exception:
        per_page = 20

    offset = (page - 1) * per_page

    with get_db() as db:
        base = db.query(Movie)
        if q:
            like = f"%{q}%"
            base = base.filter(Movie.title.ilike(like))

        total = base.count()
        rows = base.order_by(Movie.updated_at.desc()).offset(offset).limit(per_page).all()

        items = [
            {
                "id": r.id,
                "title": r.title,
                "release_date": r.release_date.isoformat() if r.release_date else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in rows
        ]

        return jsonify({
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })


@app.route("/api/tv_series")
def api_tv_series():
    """Paginated TV series listing and search."""
    q = request.args.get('q')
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 20))
    except Exception:
        per_page = 20

    offset = (page - 1) * per_page

    with get_db() as db:
        base = db.query(TVSeries)
        if q:
            like = f"%{q}%"
            base = base.filter(TVSeries.name.ilike(like))

        total = base.count()
        rows = base.order_by(TVSeries.updated_at.desc()).offset(offset).limit(per_page).all()

        items = [
            {
                "id": r.id,
                "name": r.name,
                "first_air_date": r.first_air_date.isoformat() if r.first_air_date else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in rows
        ]

        return jsonify({
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })


@app.route('/api/analysis/genres')
def api_analysis_genres():
    """Return genre distribution for analysis charts."""
    with get_db() as db:
        try:
            # Try to query the association table directly if possible, or just use raw SQL
            res = db.execute(text(
                "SELECT g.name, COUNT(mg.movie_id) as count FROM genres g "
                "JOIN movie_genres mg ON g.id = mg.genre_id "
                "GROUP BY g.id, g.name "
                "ORDER BY count DESC LIMIT 20"
            )).fetchall()
            return jsonify({"genres": [{"name": r[0], "count": r[1]} for r in res]})
        except Exception as e:
            print(f"Error querying genres: {e}")
            return jsonify({"genres": []})


@app.route('/api/analysis/people')
def api_analysis_people():
    """Return most prolific people."""
    with get_db() as db:
        try:
            res = db.execute(text(
                "SELECT p.name, COUNT(mc.movie_id) as movie_count FROM people p "
                "JOIN movie_cast mc ON p.id = mc.person_id "
                "GROUP BY p.id, p.name "
                "ORDER BY movie_count DESC LIMIT 20"
            )).fetchall()
            return jsonify({"people": [{"name": r[0], "count": r[1]} for r in res]})
        except Exception as e:
            print(f"Error querying people: {e}")
            return jsonify({"people": []})


@app.route('/api/analysis/years')
def api_analysis_years():
    """Return movie distribution by year."""
    with get_db() as db:
        try:
            res = db.execute(text(
                "SELECT EXTRACT(YEAR FROM release_date) as year, COUNT(*) as count "
                "FROM movies "
                "WHERE release_date IS NOT NULL "
                "GROUP BY year "
                "ORDER BY year DESC LIMIT 50"
            )).fetchall()
            # Sort by year ascending for the chart
            data = [{"year": int(r[0]), "count": r[1]} for r in res]
            data.sort(key=lambda x: x['year'])
            return jsonify({"years": data})
        except Exception as e:
            print(f"Error querying years: {e}")
            return jsonify({"years": []})


@app.route('/api/analysis/ratings')
def api_analysis_ratings():
    """Return movie distribution by rating."""
    with get_db() as db:
        try:
            # Group by rounded vote_average
            res = db.execute(text(
                "SELECT ROUND(vote_average) as rating, COUNT(*) as count "
                "FROM movies "
                "WHERE vote_average IS NOT NULL "
                "GROUP BY rating "
                "ORDER BY rating"
            )).fetchall()
            return jsonify({"ratings": [{"rating": int(r[0]), "count": r[1]} for r in res]})
        except Exception as e:
            print(f"Error querying ratings: {e}")
            return jsonify({"ratings": []})


@app.route('/api/analysis/top-rated-movies')
def api_analysis_top_rated():
    """Return top rated movies with significant vote count."""
    with get_db() as db:
        try:
            res = db.execute(text(
                "SELECT id, title, vote_average, vote_count, release_date "
                "FROM movies "
                "WHERE vote_count >= 1000 AND vote_average IS NOT NULL "
                "ORDER BY vote_average DESC, vote_count DESC "
                "LIMIT 20"
            )).fetchall()
            return jsonify({
                "movies": [
                    {
                        "id": r[0],
                        "title": r[1],
                        "rating": float(r[2]) if r[2] else 0,
                        "votes": r[3],
                        "year": r[4].year if r[4] else None
                    }
                    for r in res
                ]
            })
        except Exception as e:
            print(f"Error querying top rated: {e}")
            return jsonify({"movies": []})


@app.route('/api/analysis/top-production-companies')
def api_analysis_top_companies():
    """Return production companies with most movies."""
    with get_db() as db:
        try:
            res = db.execute(text(
                "SELECT pc.id, pc.name, COUNT(mpc.movie_id) as movie_count "
                "FROM production_companies pc "
                "JOIN movie_production_companies mpc ON pc.id = mpc.company_id "
                "GROUP BY pc.id, pc.name "
                "ORDER BY movie_count DESC "
                "LIMIT 20"
            )).fetchall()
            return jsonify({
                "companies": [
                    {"id": r[0], "name": r[1], "count": r[2]}
                    for r in res
                ]
            })
        except Exception as e:
            print(f"Error querying companies: {e}")
            return jsonify({"companies": []})


@app.route('/api/analysis/languages')
def api_analysis_languages():
    """Return movie distribution by original language."""
    with get_db() as db:
        try:
            res = db.execute(text(
                "SELECT original_language, COUNT(*) as count "
                "FROM movies "
                "WHERE original_language IS NOT NULL AND original_language != '' "
                "GROUP BY original_language "
                "ORDER BY count DESC "
                "LIMIT 15"
            )).fetchall()
            return jsonify({
                "languages": [
                    {"code": r[0], "count": r[1]}
                    for r in res
                ]
            })
        except Exception as e:
            print(f"Error querying languages: {e}")
            return jsonify({"languages": []})


@app.route('/api/analysis/runtime')
def api_analysis_runtime():
    """Return movie runtime distribution."""
    with get_db() as db:
        try:
            # Group runtime into buckets
            res = db.execute(text(
                "SELECT "
                "  CASE "
                "    WHEN runtime < 60 THEN 'Under 1h' "
                "    WHEN runtime < 90 THEN '1h - 1h30' "
                "    WHEN runtime < 120 THEN '1h30 - 2h' "
                "    WHEN runtime < 150 THEN '2h - 2h30' "
                "    WHEN runtime < 180 THEN '2h30 - 3h' "
                "    ELSE 'Over 3h' "
                "  END as bucket, "
                "  COUNT(*) as count "
                "FROM movies "
                "WHERE runtime IS NOT NULL AND runtime > 0 "
                "GROUP BY bucket "
                "ORDER BY MIN(runtime)"
            )).fetchall()
            return jsonify({
                "runtime": [{"bucket": r[0], "count": r[1]} for r in res]
            })
        except Exception as e:
            print(f"Error querying runtime: {e}")
            return jsonify({"runtime": []})


@app.route('/api/analysis/budget-revenue')
def api_analysis_budget_revenue():
    """Return budget vs revenue analysis for profitable movies."""
    with get_db() as db:
        try:
            # Get average stats
            stats = db.execute(text(
                "SELECT "
                "  AVG(budget) as avg_budget, "
                "  AVG(revenue) as avg_revenue, "
                "  AVG(CASE WHEN budget > 0 THEN (revenue - budget)::float / budget * 100 END) as avg_roi, "
                "  COUNT(*) FILTER (WHERE revenue > budget AND budget > 0) as profitable_count, "
                "  COUNT(*) FILTER (WHERE budget > 0 AND revenue > 0) as total_with_data "
                "FROM movies "
                "WHERE budget > 0 AND revenue > 0"
            )).fetchone()
            
            # Get top ROI movies
            top_roi = db.execute(text(
                "SELECT title, budget, revenue, "
                "  ((revenue - budget)::float / budget * 100) as roi "
                "FROM movies "
                "WHERE budget >= 1000000 AND revenue > 0 "
                "ORDER BY roi DESC "
                "LIMIT 10"
            )).fetchall()
            
            # Get biggest box office
            top_revenue = db.execute(text(
                "SELECT title, budget, revenue "
                "FROM movies "
                "WHERE revenue > 0 "
                "ORDER BY revenue DESC "
                "LIMIT 10"
            )).fetchall()
            
            return jsonify({
                "stats": {
                    "avg_budget": float(stats[0]) if stats[0] else 0,
                    "avg_revenue": float(stats[1]) if stats[1] else 0,
                    "avg_roi": float(stats[2]) if stats[2] else 0,
                    "profitable_count": stats[3] or 0,
                    "total_with_data": stats[4] or 0
                },
                "top_roi": [
                    {
                        "title": r[0],
                        "budget": r[1],
                        "revenue": r[2],
                        "roi": float(r[3]) if r[3] else 0
                    }
                    for r in top_roi
                ],
                "top_revenue": [
                    {"title": r[0], "budget": r[1], "revenue": r[2]}
                    for r in top_revenue
                ]
            })
        except Exception as e:
            print(f"Error querying budget/revenue: {e}")
            return jsonify({"stats": {}, "top_roi": [], "top_revenue": []})


@app.route('/api/analysis/tv-stats')
def api_analysis_tv_stats():
    """Return TV series statistics."""
    with get_db() as db:
        try:
            # Status distribution
            status_dist = db.execute(text(
                "SELECT status, COUNT(*) as count "
                "FROM tv_series "
                "WHERE status IS NOT NULL AND status != '' "
                "GROUP BY status "
                "ORDER BY count DESC"
            )).fetchall()
            
            # Average seasons/episodes
            avg_stats = db.execute(text(
                "SELECT "
                "  AVG(number_of_seasons) as avg_seasons, "
                "  AVG(number_of_episodes) as avg_episodes, "
                "  MAX(number_of_seasons) as max_seasons, "
                "  MAX(number_of_episodes) as max_episodes "
                "FROM tv_series "
                "WHERE number_of_seasons > 0"
            )).fetchone()
            
            # Longest running shows
            longest = db.execute(text(
                "SELECT name, number_of_seasons, number_of_episodes, first_air_date "
                "FROM tv_series "
                "WHERE number_of_episodes > 0 "
                "ORDER BY number_of_episodes DESC "
                "LIMIT 10"
            )).fetchall()
            
            # Top rated TV shows
            top_rated_tv = db.execute(text(
                "SELECT name, vote_average, vote_count "
                "FROM tv_series "
                "WHERE vote_count >= 500 AND vote_average IS NOT NULL "
                "ORDER BY vote_average DESC "
                "LIMIT 10"
            )).fetchall()
            
            return jsonify({
                "status_distribution": [
                    {"status": r[0], "count": r[1]} for r in status_dist
                ],
                "averages": {
                    "avg_seasons": float(avg_stats[0]) if avg_stats[0] else 0,
                    "avg_episodes": float(avg_stats[1]) if avg_stats[1] else 0,
                    "max_seasons": avg_stats[2] or 0,
                    "max_episodes": avg_stats[3] or 0
                },
                "longest_running": [
                    {
                        "name": r[0],
                        "seasons": r[1],
                        "episodes": r[2],
                        "first_air_date": r[3].isoformat() if r[3] else None
                    }
                    for r in longest
                ],
                "top_rated": [
                    {"name": r[0], "rating": float(r[1]) if r[1] else 0, "votes": r[2]}
                    for r in top_rated_tv
                ]
            })
        except Exception as e:
            print(f"Error querying TV stats: {e}")
            return jsonify({
                "status_distribution": [],
                "averages": {},
                "longest_running": [],
                "top_rated": []
            })


@app.route('/api/analysis/decades')
def api_analysis_decades():
    """Return movie distribution by decade."""
    with get_db() as db:
        try:
            res = db.execute(text(
                "SELECT "
                "  (EXTRACT(YEAR FROM release_date)::int / 10 * 10) as decade, "
                "  COUNT(*) as count, "
                "  AVG(vote_average) as avg_rating "
                "FROM movies "
                "WHERE release_date IS NOT NULL "
                "GROUP BY decade "
                "ORDER BY decade"
            )).fetchall()
            return jsonify({
                "decades": [
                    {
                        "decade": f"{int(r[0])}s",
                        "count": r[1],
                        "avg_rating": round(float(r[2]), 2) if r[2] else 0
                    }
                    for r in res if r[0] is not None
                ]
            })
        except Exception as e:
            print(f"Error querying decades: {e}")
            return jsonify({"decades": []})


@app.route('/api/system/stats')
def api_system_stats():
    """Return system status."""
    with get_db() as db:
        try:
            # Get DB size
            size_res = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
            
            return jsonify({
                "db_size": size_res,
                "status": "Connected",
                "last_update": utcnow().isoformat()
            })
        except Exception as e:
            return jsonify({
                "db_size": "Unknown",
                "status": "Error",
                "last_update": utcnow().isoformat()
            }), 500


@app.route("/api/db/download")
def download_db():
    """Stream a database dump."""
    def generate():
        env = {'PGPASSWORD': config.DB_PASSWORD}
        cmd = [
            'pg_dump',
            '-h', config.DB_HOST,
            '-p', str(config.DB_PORT),
            '-U', config.DB_USER,
            config.DB_NAME
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        for line in process.stdout:
            yield line

    return Response(
        stream_with_context(generate()),
        mimetype='application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename=tmdb_dump_{datetime.now().strftime("%Y%m%d")}.sql'
        }
    )


@app.route("/api/query/schema")
def api_query_schema():
    """Get database schema."""
    with get_db() as db:
        inspector = inspect(db.get_bind())
        tables = []
        
        for table_name in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"])
                })
            tables.append({
                "name": table_name,
                "columns": columns
            })
            
        return jsonify({"tables": tables})


@app.route("/api/query/run", methods=["POST"])
def api_query_run():
    """Run a read-only SQL query."""
    data = request.get_json()
    sql = data.get("sql", "").strip()
    
    if not sql:
        return jsonify({"error": "Empty query"}), 400
    
    # Remove trailing semicolons and whitespace
    sql = sql.rstrip(';').strip()
    
    # Security checks - only allow SELECT queries
    sql_upper = sql.upper()
    
    # Check if it starts with SELECT
    if not sql_upper.startswith("SELECT"):
        return jsonify({"error": "Only SELECT queries are allowed in SQL Lab"}), 400
    
    # Block dangerous keywords that could modify data or affect system
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
        'PG_TERMINATE_BACKEND', 'PG_CANCEL_BACKEND', 'COPY',
        'VACUUM', 'ANALYZE', 'CLUSTER', 'LOCK', 'REINDEX'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return jsonify({"error": f"Keyword '{keyword}' is not allowed in read-only mode"}), 400
    
    # Check for multiple statements (semicolons in the middle)
    if ';' in sql:
        return jsonify({"error": "Multiple SQL statements are not allowed"}), 400
        
    with get_db() as db:
        try:
            # Set transaction to read-only for extra safety
            db.execute(text("SET TRANSACTION READ ONLY"))
            
            # Execute query
            result = db.execute(text(sql))
            
            # Get column names
            columns = list(result.keys())
            
            # Get rows (limit to 1000 for safety)
            rows = []
            for row in result.fetchmany(1000):
                # Convert row to list and handle non-serializable types if necessary
                row_data = []
                for cell in row:
                    if isinstance(cell, datetime):
                        row_data.append(cell.isoformat())
                    else:
                        row_data.append(cell)
                rows.append(row_data)
            
            # Rollback to ensure no changes (even though transaction is read-only)
            db.rollback()
                
            return jsonify({
                "columns": columns,
                "rows": rows
            })
            
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 400


@app.route("/api/query/saved", methods=["GET"])
def api_query_saved_list():
    """Get list of saved queries."""
    with get_db() as db:
        try:
            queries = db.query(SavedQuery).order_by(SavedQuery.updated_at.desc()).all()
            return jsonify({
                "queries": [
                    {
                        "id": q.id,
                        "name": q.name,
                        "description": q.description,
                        "query_text": q.query_text,
                        "created_at": q.created_at.isoformat() if q.created_at else None,
                        "updated_at": q.updated_at.isoformat() if q.updated_at else None
                    }
                    for q in queries
                ]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400


@app.route("/api/query/saved", methods=["POST"])
def api_query_saved_create():
    """Save a new query."""
    data = request.get_json()
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    query_text = data.get("query_text", "").strip()
    
    if not name:
        return jsonify({"error": "Query name is required"}), 400
    
    if not query_text:
        return jsonify({"error": "Query text is required"}), 400
    
    with get_db() as db:
        try:
            saved_query = SavedQuery(
                name=name,
                description=description,
                query_text=query_text
            )
            db.add(saved_query)
            db.commit()
            
            return jsonify({
                "id": saved_query.id,
                "name": saved_query.name,
                "description": saved_query.description,
                "query_text": saved_query.query_text,
                "created_at": saved_query.created_at.isoformat() if saved_query.created_at else None
            })
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 400


@app.route("/api/query/saved/<int:query_id>", methods=["DELETE"])
def api_query_saved_delete(query_id):
    """Delete a saved query."""
    with get_db() as db:
        try:
            query = db.query(SavedQuery).filter(SavedQuery.id == query_id).first()
            if not query:
                return jsonify({"error": "Query not found"}), 404
            
            db.delete(query)
            db.commit()
            
            return jsonify({"message": "Query deleted successfully"})
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 400


def run_dashboard():
    """Run the dashboard server."""
    app.run(
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        debug=False
    )
