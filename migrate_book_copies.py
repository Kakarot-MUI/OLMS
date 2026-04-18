import os
import sys
from sqlalchemy import text

# Setup Flask app context
from app import create_app, db
from app.models import Book, BookCopy

app = create_app()

with app.app_context():
    print("Starting Book Copy Migration...")
    
    # 1. Ensure new tables are created (BookCopy)
    db.create_all()
    print("Table checking complete.")

    # 2. Manually add copy_id to issued_books if it doesn't exist
    try:
        db.session.execute(text('ALTER TABLE issued_books ADD COLUMN copy_id INTEGER'))
        db.session.commit()
        print("Added copy_id column to issued_books table.")
    except Exception as e:
        db.session.rollback()
        print("Note: copy_id column already exists or alter skipped.")

    # 3. Migrate existing aggregate access numbers into individual BookCopy records
    books = Book.query.all()
    count = 0
    for book in books:
        if book.copies.count() == 0:
            if book.access_number:
                # E.g., "4, 15" -> ["4", "15"]
                access_numbers = [num.strip() for num in book.access_number.split(',') if num.strip()]
            else:
                # Fallback if no access number exists
                access_numbers = [f"B{book.id}-{i+1}" for i in range(book.total_copies)]
                
            for acc_num in access_numbers:
                copy = BookCopy(
                    book_id=book.id,
                    access_number=acc_num,
                    status='available'
                )
                db.session.add(copy)
                count += 1
                
    db.session.commit()
    print(f"Migration complete! Automatically generated {count} individual copy tracking records.")
