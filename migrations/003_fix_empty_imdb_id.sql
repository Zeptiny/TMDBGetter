-- Migration: 003_fix_empty_imdb_id.sql
-- Description: Convert empty string imdb_id values to NULL to avoid unique constraint violations
-- Date: 2025-11-25

-- ============================================
-- Fix empty string imdb_id values in movies (convert to NULL)
-- Many movies don't have IMDB IDs, so TMDB returns empty string ''
-- The unique constraint only allows one empty string, causing violations
-- ============================================

UPDATE movies SET imdb_id = NULL WHERE imdb_id = '';

-- Verify the fix (optional - run manually)
-- SELECT COUNT(*) FROM movies WHERE imdb_id = '';
-- Should return 0
