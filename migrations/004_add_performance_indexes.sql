-- Migration: Add performance indexes
-- Date: 2025-11-25
-- Description: Add indexes to improve query performance and reduce CPU usage

-- Processing State indexes (heavily queried)
CREATE INDEX IF NOT EXISTS idx_processing_state_status ON processing_state(status);
CREATE INDEX IF NOT EXISTS idx_processing_state_content_type ON processing_state(content_type);
CREATE INDEX IF NOT EXISTS idx_processing_state_content_type_status ON processing_state(content_type, status);
CREATE INDEX IF NOT EXISTS idx_processing_state_completed_at ON processing_state(completed_at);
CREATE INDEX IF NOT EXISTS idx_processing_state_last_attempt_at ON processing_state(last_attempt_at);

-- Movie indexes for analysis queries
CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date);
CREATE INDEX IF NOT EXISTS idx_movies_vote_average ON movies(vote_average);
CREATE INDEX IF NOT EXISTS idx_movies_vote_count ON movies(vote_count);
CREATE INDEX IF NOT EXISTS idx_movies_original_language ON movies(original_language);
CREATE INDEX IF NOT EXISTS idx_movies_runtime ON movies(runtime);
CREATE INDEX IF NOT EXISTS idx_movies_budget ON movies(budget) WHERE budget > 0;
CREATE INDEX IF NOT EXISTS idx_movies_revenue ON movies(revenue) WHERE revenue > 0;
CREATE INDEX IF NOT EXISTS idx_movies_updated_at ON movies(updated_at);

-- TV Series indexes for analysis queries
CREATE INDEX IF NOT EXISTS idx_tv_series_status ON tv_series(status);
CREATE INDEX IF NOT EXISTS idx_tv_series_vote_average ON tv_series(vote_average);
CREATE INDEX IF NOT EXISTS idx_tv_series_vote_count ON tv_series(vote_count);
CREATE INDEX IF NOT EXISTS idx_tv_series_number_of_episodes ON tv_series(number_of_episodes);
CREATE INDEX IF NOT EXISTS idx_tv_series_first_air_date ON tv_series(first_air_date);
CREATE INDEX IF NOT EXISTS idx_tv_series_updated_at ON tv_series(updated_at);

-- Association table indexes for JOIN performance
CREATE INDEX IF NOT EXISTS idx_movie_genres_genre_id ON movie_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_movie_genres_movie_id ON movie_genres(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_cast_person_id ON movie_cast(person_id);
CREATE INDEX IF NOT EXISTS idx_movie_cast_movie_id ON movie_cast(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_crew_person_id ON movie_crew(person_id);
CREATE INDEX IF NOT EXISTS idx_movie_crew_movie_id ON movie_crew(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_production_companies_company_id ON movie_production_companies(company_id);
CREATE INDEX IF NOT EXISTS idx_movie_production_companies_movie_id ON movie_production_companies(movie_id);

-- Daily dumps index
CREATE INDEX IF NOT EXISTS idx_daily_dumps_dump_date ON daily_dumps(dump_date);
CREATE INDEX IF NOT EXISTS idx_daily_dumps_dump_type ON daily_dumps(dump_type);

-- Run ANALYZE to update statistics after adding indexes
ANALYZE processing_state;
ANALYZE movies;
ANALYZE tv_series;
ANALYZE movie_genres;
ANALYZE movie_cast;
ANALYZE movie_crew;
ANALYZE movie_production_companies;
ANALYZE daily_dumps;
