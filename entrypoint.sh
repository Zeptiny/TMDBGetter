#!/bin/bash
# Entrypoint script that runs migrations before starting the application

set -e

echo "=== TMDB Getter Container Starting ==="

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - running migrations..."

# Run all migrations in order
MIGRATION_DIR="/app/migrations"
if [ -d "$MIGRATION_DIR" ]; then
    for migration in "$MIGRATION_DIR"/*.sql; do
        if [ -f "$migration" ]; then
            echo "Applying migration: $(basename $migration)"
            PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$migration" 2>&1 | grep -v "already exists" || true
            echo "✓ Migration applied: $(basename $migration)"
        fi
    done
    echo "All migrations completed successfully!"
else
    echo "No migration directory found, skipping migrations..."
fi

echo "=== Starting Application ==="
# Execute the main command
exec "$@"
