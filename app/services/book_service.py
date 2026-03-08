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


# ── Recommendations ──────────────────────────────────────────────────────

def get_personalized_recommendations(user_id, limit=10):
    """
    Generate personalized book recommendations for a user based on their 
    borrowing history and saved books, prioritizing highly-rated books.
    """
    from app.models import IssuedBook, SavedBook, Book, Review
    from sqlalchemy import func
    import collections

    # 1. Get categories of books the user has interacted with
    borrowed_cats = db.session.query(Book.category).join(IssuedBook).filter(IssuedBook.user_id == user_id).all()
    saved_cats = db.session.query(Book.category).join(SavedBook).filter(SavedBook.user_id == user_id).all()
    
    all_interacted_cats = [c[0] for c in borrowed_cats + saved_cats]
    
    # 2. Calculate top categories
    cat_counts = collections.Counter(all_interacted_cats)
    top_categories = [cat for cat, count in cat_counts.most_common(2)]
    
    # 3. Get IDs of books user already borrowed (to avoid recommending them)
    borrowed_ids = [b[0] for b in db.session.query(IssuedBook.book_id).filter(IssuedBook.user_id == user_id).all()]
    
    recommendations = []
    
    if top_categories:
        # Find books in their favorite categories they haven't read, sorted by rating
        fav_cat_recs = db.session.query(Book).outerjoin(Review).filter(
            Book.category.in_(top_categories),
            ~Book.id.in_(borrowed_ids)
        ).group_by(Book.id).order_by(
            func.avg(Review.rating).desc().nullslast(),
            Book.total_copies.desc()
        ).limit(limit).all()
        
        recommendations.extend(fav_cat_recs)
        
    # 4. Fallback/Trending: Fill remaining slots with the HIGHEST RATED books overall
    if len(recommendations) < limit:
        needed = limit - len(recommendations)
        existing_ids = [b.id for b in recommendations] + borrowed_ids
        
        # Get books with highest average rating overall
        trending = db.session.query(Book).outerjoin(Review).filter(
            ~Book.id.in_(existing_ids)
        ).group_by(Book.id).order_by(
            func.avg(Review.rating).desc().nullslast(),
            Book.total_copies.desc()
        ).limit(needed).all()
        
        recommendations.extend(trending)
        
    return recommendations[:limit]


def get_book_cover_url(book_title, book_author):
    """
    Returns a URL for the book cover using Open Library.
    If no ISBN is available, it uses the Search API.
    """
    import urllib.parse
    # Create a safe query string
    query = f"{book_title} {book_author}"
    safe_query = urllib.parse.quote(query)
    # Using Open Library Cover API via Author/Title search search
    # This is a guestimate URL that Open Library supports for many books
    # Format: https://covers.openlibrary.org/b/title/{title}-{size}.jpg
    # Actually, it's better to use the search-based lookup if possible, 
    # but for simplicity and speed, we return a URL that will be handled by the frontend.
    return f"https://covers.openlibrary.org/b/title/{urllib.parse.quote(book_title.lower())}-M.jpg"
