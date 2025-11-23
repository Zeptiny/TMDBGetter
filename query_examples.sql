-- TMDB Data Query Examples
-- Use these queries to verify data is being collected correctly

-- ============================================
-- BASIC COUNTS
-- ============================================

-- Total movies processed
SELECT COUNT(*) as total_movies FROM movies;

-- Total TV series processed
SELECT COUNT(*) as total_tv_series FROM tv_series;

-- Total people (actors, directors, crew)
SELECT COUNT(*) as total_people FROM people;

-- Total keywords
SELECT COUNT(*) as total_keywords FROM keywords;

-- Total genres
SELECT COUNT(*) as total_genres FROM genres;


-- ============================================
-- DETAILED STATISTICS
-- ============================================

-- Movies with complete data (with genres, keywords, cast)
SELECT 
    COUNT(DISTINCT m.id) as movies_with_genres
FROM movies m
INNER JOIN movie_genres mg ON m.id = mg.movie_id;

SELECT 
    COUNT(DISTINCT m.id) as movies_with_keywords
FROM movies m
INNER JOIN movie_keywords mk ON m.id = mk.movie_id;

SELECT 
    COUNT(DISTINCT m.id) as movies_with_cast
FROM movies m
INNER JOIN movie_cast mc ON m.id = mc.movie_id;

-- TV series statistics
SELECT 
    COUNT(DISTINCT tv.id) as tv_with_networks
FROM tv_series tv
INNER JOIN tv_series_networks tvn ON tv.id = tvn.tv_series_id;

SELECT 
    COUNT(DISTINCT tv.id) as tv_with_keywords
FROM tv_series tv
INNER JOIN tv_series_keywords tvk ON tv.id = tvk.tv_series_id;


-- ============================================
-- RECENT DATA SAMPLES
-- ============================================

-- Top 10 most recent movies (by updated_at)
SELECT 
    id,
    title,
    release_date,
    vote_average,
    vote_count,
    updated_at
FROM movies
ORDER BY updated_at DESC
LIMIT 10;

-- Top 10 highest rated movies (with at least 100 votes)
SELECT 
    id,
    title,
    release_date,
    vote_average,
    vote_count,
    popularity
FROM movies
WHERE vote_count >= 100
ORDER BY vote_average DESC, vote_count DESC
LIMIT 10;

-- Sample movie with all related data
SELECT 
    m.title,
    m.release_date,
    m.vote_average,
    COUNT(DISTINCT mg.genre_id) as genre_count,
    COUNT(DISTINCT mk.keyword_id) as keyword_count,
    COUNT(DISTINCT mc.person_id) as cast_count,
    COUNT(DISTINCT mcr.person_id) as crew_count
FROM movies m
LEFT JOIN movie_genres mg ON m.id = mg.movie_id
LEFT JOIN movie_keywords mk ON m.id = mk.movie_id
LEFT JOIN movie_cast mc ON m.id = mc.movie_id
LEFT JOIN movie_crew mcr ON m.id = mcr.movie_id
WHERE m.id = (SELECT id FROM movies ORDER BY updated_at DESC LIMIT 1)
GROUP BY m.id, m.title, m.release_date, m.vote_average;


-- ============================================
-- DATA QUALITY CHECKS
-- ============================================

-- Movies missing basic information
SELECT 
    COUNT(*) as movies_without_title
FROM movies
WHERE title IS NULL OR title = '';

SELECT 
    COUNT(*) as movies_without_release_date
FROM movies
WHERE release_date IS NULL;

SELECT 
    COUNT(*) as movies_with_genres
FROM movies m
WHERE EXISTS (SELECT 1 FROM movie_genres mg WHERE mg.movie_id = m.id);

-- External IDs coverage
SELECT 
    COUNT(*) as movies_with_external_ids
FROM external_ids_movies;

SELECT 
    COUNT(*) as tv_with_external_ids
FROM external_ids_tv_series;


-- ============================================
-- POPULAR GENRES
-- ============================================

-- Most common movie genres
SELECT 
    g.name,
    COUNT(mg.movie_id) as movie_count
FROM genres g
INNER JOIN movie_genres mg ON g.id = mg.genre_id
GROUP BY g.id, g.name
ORDER BY movie_count DESC;


-- ============================================
-- MOST PROLIFIC PEOPLE
-- ============================================

-- Actors with most movie appearances
SELECT 
    p.name,
    COUNT(mc.movie_id) as movie_count,
    p.popularity
FROM people p
INNER JOIN movie_cast mc ON p.id = mc.person_id
GROUP BY p.id, p.name, p.popularity
ORDER BY movie_count DESC
LIMIT 20;

-- Directors with most movies
SELECT 
    p.name,
    COUNT(DISTINCT mcr.movie_id) as movie_count
FROM people p
INNER JOIN movie_crew mcr ON p.id = mcr.person_id
WHERE mcr.job = 'Director'
GROUP BY p.id, p.name
ORDER BY movie_count DESC
LIMIT 20;


-- ============================================
-- PROCESSING STATE
-- ============================================

-- Check processing state summary
SELECT 
    state,
    COUNT(*) as count
FROM processing_state_movies
GROUP BY state
ORDER BY state;

SELECT 
    state,
    COUNT(*) as count
FROM processing_state_tv_series
GROUP BY state
ORDER BY state;

-- Recently failed items
SELECT 
    tmdb_id,
    error_message,
    retry_count,
    last_attempt
FROM processing_state_movies
WHERE state = 'failed'
ORDER BY last_attempt DESC
LIMIT 10;


-- ============================================
-- COMPLETE MOVIE EXAMPLE
-- ============================================

-- Get all details for a specific movie (replace ID as needed)
SELECT 
    m.*,
    string_agg(DISTINCT g.name, ', ') as genres,
    string_agg(DISTINCT pc.name, ', ') as production_companies
FROM movies m
LEFT JOIN movie_genres mg ON m.id = mg.movie_id
LEFT JOIN genres g ON mg.genre_id = g.id
LEFT JOIN movie_production_companies mpc ON m.id = mpc.movie_id
LEFT JOIN production_companies pc ON mpc.company_id = pc.id
WHERE m.id = (SELECT id FROM movies ORDER BY popularity DESC LIMIT 1)
GROUP BY m.id;

-- Get cast for a movie
SELECT 
    p.name,
    mc.character,
    mc.cast_order
FROM movie_cast mc
INNER JOIN people p ON mc.person_id = p.id
WHERE mc.movie_id = (SELECT id FROM movies ORDER BY popularity DESC LIMIT 1)
ORDER BY mc.cast_order
LIMIT 10;
