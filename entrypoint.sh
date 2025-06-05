#!/bin/sh

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
until uv run python -c "import psycopg; psycopg.connect('host=db port=5432 user=postgres password=postgres dbname=blockhaus101_django')" 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done
echo "PostgreSQL started"

# Run migrations
echo "Running migrations..."
uv run python manage.py migrate

# Collect static files
echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

# Start server
echo "Starting server..."
exec uv run gunicorn blockhaus101.asgi:application -w 4 -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-8000}"
