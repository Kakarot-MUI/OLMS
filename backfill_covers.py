import os
import sys
import time

# Add current directory to path
sys.path.append(os.path.abspath(os.curdir))

os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_RKQVm9tuzlP1@ep-autumn-flower-amtm02j8.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require'
os.environ['FLASK_ENV'] = 'production'

try:
    from app import create_app, db
    from app.models import Book
    from app.services.book_service import get_book_cover_url
    
    app = create_app('production')
    with app.app_context():
        # Find books that are missing covers OR have the old broken title-search format
        books = Book.query.filter(
            (Book.image_url == None) | 
            (Book.image_url.like('%/b/title/%'))
        ).all()
        
        print(f"Found {len(books)} books to update...")
        
        updated_count = 0
        for book in books:
            print(f"Fetching cover for: {book.title} ({book.author})...")
            new_url = get_book_cover_url(book.title, book.author)
            
            if new_url:
                book.image_url = new_url
                updated_count += 1
                print(f"  --> Updated: {new_url}")
            else:
                print(f"  --> No cover found.")
            
            # Rate limiting to be kind to Open Library
            time.sleep(1)
            
            # Commit every 5 books for safety
            if updated_count % 5 == 0:
                db.session.commit()
        
        db.session.commit()
        print(f"\nFINISHED! Successfully updated covers for {updated_count} books.")

except Exception as e:
    print(f"BACKFILL FAILED: {e}")
    sys.exit(1)
