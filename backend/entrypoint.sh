#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Start Gunicorn
exec gunicorn api.app:app --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 60
