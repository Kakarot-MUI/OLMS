import sys
import os
from flask import Flask

# Add current directory to path
sys.path.append(os.path.abspath(os.curdir))

try:
    from app import create_app, db
    
    # Set the environment variable for this process
    os.environ['DATABASE_URL'] = "postgresql://neondb_owner:npg_RKQVm9tuzlP1@ep-autumn-flower-amtm02j8.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"
    os.environ['FLASK_CONFIG'] = 'production'
    
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Successfully created all database tables in Neon!")
except Exception as e:
    print(f"Error initializing database: {e}")
    sys.exit(1)
