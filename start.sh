#!/bin/bash
echo "Running master database synchronization..."
python migrate_master.py
echo "Starting Gunicorn server..."
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
