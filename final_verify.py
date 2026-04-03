import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.abspath(os.curdir))

os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_RKQVm9tuzlP1@ep-autumn-flower-amtm02j8.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require'
os.environ['FLASK_ENV'] = 'production'

try:
    from app import create_app, db
    from app.models import Book
    
    app = create_app('production')
    with app.app_context():
        # This will trigger the auto-migration AND a query
        count = Book.query.count()
        print(f"SUCCESS: Database connection is active. Total books in library: {count}")
        print("MIGRATION: Verification complete and successful!")
except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    sys.exit(1)
