-- Migration: Add saved_queries table
-- Date: 2025-11-23
-- Description: Create table to store user's saved SQL queries in the SQL Lab

CREATE TABLE IF NOT EXISTS saved_queries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups by update date
CREATE INDEX IF NOT EXISTS idx_saved_queries_updated_at ON saved_queries(updated_at DESC);

-- Add comment to table
COMMENT ON TABLE saved_queries IS 'Stores user-saved SQL queries from the SQL Lab interface';
COMMENT ON COLUMN saved_queries.name IS 'User-friendly name for the query';
COMMENT ON COLUMN saved_queries.description IS 'Optional description of what the query does';
COMMENT ON COLUMN saved_queries.query_text IS 'The actual SQL query text';
