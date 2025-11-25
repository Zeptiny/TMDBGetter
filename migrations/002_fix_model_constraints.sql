-- Migration: 002_fix_model_constraints.sql
-- Description: Remove incorrect unique constraints and imdb_id from tv_series
-- Date: 2025-11-25

-- ============================================
-- 1. Remove UNIQUE constraint on credit_id in movie_cast
-- ============================================
-- PostgreSQL: Drop the unique index/constraint
ALTER TABLE movie_cast DROP CONSTRAINT IF EXISTS movie_cast_credit_id_key;
DROP INDEX IF EXISTS ix_movie_cast_credit_id;

-- ============================================
-- 2. Remove UNIQUE constraint on credit_id in movie_crew
-- ============================================
ALTER TABLE movie_crew DROP CONSTRAINT IF EXISTS movie_crew_credit_id_key;
DROP INDEX IF EXISTS ix_movie_crew_credit_id;

-- ============================================
-- 3. Remove UNIQUE constraint on credit_id in tv_series_cast
-- ============================================
ALTER TABLE tv_series_cast DROP CONSTRAINT IF EXISTS tv_series_cast_credit_id_key;
DROP INDEX IF EXISTS ix_tv_series_cast_credit_id;

-- ============================================
-- 4. Remove UNIQUE constraint on credit_id in tv_series_crew
-- ============================================
ALTER TABLE tv_series_crew DROP CONSTRAINT IF EXISTS tv_series_crew_credit_id_key;
DROP INDEX IF EXISTS ix_tv_series_crew_credit_id;

-- ============================================
-- 5. Remove imdb_id column from tv_series table
-- ============================================
ALTER TABLE tv_series DROP COLUMN IF EXISTS imdb_id;

-- ============================================
-- Verification queries (run manually to check)
-- ============================================
-- SELECT constraint_name FROM information_schema.table_constraints 
-- WHERE table_name = 'movie_cast' AND constraint_type = 'UNIQUE';
--
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name = 'tv_series' AND column_name = 'imdb_id';
