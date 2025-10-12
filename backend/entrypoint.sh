#!/bin/sh

# Run database migrations if enabled
if [ "${DB_AUTO_MIGRATE:-1}" = "1" ]; then
    echo "Running database migrations..."
    python -c "from services.db.migrations import apply_migrations; apply_migrations()" || {
        echo "Warning: Database migrations failed, but continuing to start server..."
        echo "This is expected if migrations have already been applied."
    }
else
    echo "Skipping database migrations (DB_AUTO_MIGRATE=0)"
fi

# Start Gunicorn
exec gunicorn api.app:app --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 60