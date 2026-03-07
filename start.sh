#!/bin/bash
echo "Running database migrations..."
flask db upgrade

echo "Starting Gunicorn server..."
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
