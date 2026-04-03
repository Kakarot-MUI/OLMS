#!/bin/bash
echo "Starting Gunicorn server..."
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
