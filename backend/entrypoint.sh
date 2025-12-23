#!/bin/sh

# Run database migrations if enabled
if [ "${DB_AUTO_MIGRATE:-1}" = "1" ]; then
    echo "Running database migrations..."
    python -c "from services.db.migrations import apply_migrations; apply_migrations()" || {
        if [ "${DB_MIGRATIONS_ALLOW_FAILURE:-0}" = "1" ]; then
            echo "Warning: Database migrations failed, but continuing (DB_MIGRATIONS_ALLOW_FAILURE=1)."
            echo "System behavior may be incorrect until schema is fixed."
        else
            echo "ERROR: Database migrations failed. Refusing to start server."
            echo "Set DB_MIGRATIONS_ALLOW_FAILURE=1 to override (not recommended for production)."
            exit 1
        fi
    }
else
    echo "Skipping database migrations (DB_AUTO_MIGRATE=0)"
fi

# Start Gunicorn
exec gunicorn api.app:app --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 60
