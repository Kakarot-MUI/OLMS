#!/bin/bash
echo "Running database upgrades..."
python migrate_publication.py
echo "Starting Gunicorn server..."
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
