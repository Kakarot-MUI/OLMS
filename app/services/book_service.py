from app import db
from app.models import Book


def get_all_books():
    """Get all books ordered by newest first."""
    return Book.query.order_by(Book.created_at.desc()).all()


def get_book_by_id(book_id):
    """Get a book by its ID."""
    return Book.query.get_or_404(book_id)


def create_book(title, author, category, total_copies):
    """Create a new book."""
    book = Book(
        title=title.strip(),
        author=author.strip(),
        category=category.strip(),
        total_copies=total_copies,
        available_copies=total_copies,
    )
    db.session.add(book)
    db.session.commit()
    return book


def update_book(book_id, title, author, category, total_copies):
    """Update an existing book."""
    book = Book.query.get_or_404(book_id)
    old_total = book.total_copies
    difference = total_copies - old_total
    new_available = book.available_copies + difference

    if new_available < 0:
        raise ValueError(
            f'Cannot reduce total copies below the number currently issued. '
            f'Currently {old_total - book.available_copies} copies are issued.'
        )

    book.title = title.strip()
    book.author = author.strip()
    book.category = category.strip()
    book.total_copies = total_copies
    book.available_copies = new_available
    db.session.commit()
    return book


def delete_book(book_id):
    """Delete a book if no copies are currently issued. Safe-deletes history."""
    book = Book.query.get_or_404(book_id)
    issued_count = book.total_copies - book.available_copies
    if issued_count > 0:
        raise ValueError(
            f'Cannot delete this book. {issued_count} copies are currently issued.'
        )
    
    # Delete associated issue history to prevent foreign key 500 errors
    from app.models import IssuedBook, SavedBook, Review
    IssuedBook.query.filter_by(book_id=book.id).delete()
    SavedBook.query.filter_by(book_id=book.id).delete()
    Review.query.filter_by(book_id=book.id).delete()
    
    db.session.delete(book)
    db.session.commit()


def search_books(query=None, category=None, page=1, per_page=12):
    """Search books by title/author with optional category filter."""
    q = Book.query

    if query:
        search_term = f'%{query.strip()}%'
        q = q.filter(
            db.or_(
                Book.title.ilike(search_term),
                Book.author.ilike(search_term)
            )
        )

    if category:
        q = q.filter(Book.category == category)

    q = q.order_by(Book.title.asc())
    return q.paginate(page=page, per_page=per_page, error_out=False)


def get_all_categories():
    """Get all distinct book categories."""
    results = db.session.query(Book.category).distinct().order_by(Book.category).all()
    return [r[0] for r in results]


# ── Saved Books ──────────────────────────────────────────────────────────

def save_book(user_id, book_id):
    """Save a book for a user."""
    from app.models import SavedBook
    if not is_book_saved(user_id, book_id):
        saved = SavedBook(user_id=user_id, book_id=book_id)
        db.session.add(saved)
        db.session.commit()

def unsave_book(user_id, book_id):
    """Remove a book from a user's saved list."""
    from app.models import SavedBook
    SavedBook.query.filter_by(user_id=user_id, book_id=book_id).delete()
    db.session.commit()

def get_user_saved_books(user_id):
    """Get all saved books for a user."""
    from app.models import SavedBook
    return SavedBook.query.filter_by(user_id=user_id).order_by(SavedBook.saved_at.desc()).all()

def is_book_saved(user_id, book_id):
    """Check if a user has saved a specific book."""
    from app.models import SavedBook
    return SavedBook.query.filter_by(user_id=user_id, book_id=book_id).first() is not None


# ── Book Reviews ─────────────────────────────────────────────────────────

def add_review(user_id, book_id, rating, content):
    """Add or update a book review."""
    from app.models import Review
    review = Review.query.filter_by(user_id=user_id, book_id=book_id).first()
    if review:
        review.rating = rating
        review.content = content
    else:
        review = Review(user_id=user_id, book_id=book_id, rating=rating, content=content)
        db.session.add(review)
    db.session.commit()

def get_book_reviews(book_id):
    """Get all reviews for a book."""
    from app.models import Review
    return Review.query.filter_by(book_id=book_id).order_by(Review.created_at.desc()).all()

def get_user_review_for_book(user_id, book_id):
    """Get a user's specific review for a book."""
    from app.models import Review
    return Review.query.filter_by(user_id=user_id, book_id=book_id).first()

def get_book_average_rating(book_id):
    """Calculate the average rating for a book."""
    from app.models import Review
    from sqlalchemy import func
    result = db.session.query(func.avg(Review.rating)).filter(Review.book_id == book_id).scalar()
    if result is None:
        return 0.0
    return round(float(result), 1)
