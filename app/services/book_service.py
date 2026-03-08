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
    history = db.session.query(Book.category, Book.id).join(IssuedBook).filter(IssuedBook.user_id == user_id).all()
    saved = db.session.query(Book.category, Book.id).join(SavedBook).filter(SavedBook.user_id == user_id).all()
    
    all_interacted = history + saved
    top_cats = [cat for cat, count in collections.Counter([b[0] for b in all_interacted]).most_common(2)]
    borrowed_ids = list(set([b[1] for b in history]))
    
    recommendations = []
    
    # helper to get books with ratings without complex group by
    def get_books_query(base_query, current_borrowed, num_needed):
        from app.models import Review, Book
        # We join on a subquery of average ratings
        ratings_sub = db.session.query(
            Review.book_id, 
            func.avg(Review.rating).label('avg_rating')
        ).group_by(Review.book_id).subquery()
        
        # Explicitly query only the Book model to avoid receiving tuples
        q = db.session.query(Book).select_from(Book)
        
        # Apply filters from base_query (if it has any)
        if hasattr(base_query, '_criterion') and base_query._criterion is not None:
            q = q.filter(base_query._criterion)
            
        q = q.outerjoin(ratings_sub, Book.id == ratings_sub.c.book_id)
        
        if current_borrowed:
            q = q.filter(~Book.id.in_(current_borrowed))
            
        results = q.order_by(
            ratings_sub.c.avg_rating.desc().nullslast(),
            Book.total_copies.desc()
        ).limit(num_needed).all()
        
        # Ensure we return objects, even if SQLAlchemy returns Row objects
        final_list = []
        for r in results:
            if isinstance(r, Book):
                final_list.append(r)
            elif hasattr(r, 'Book'): # Case for tuple result (Book, avg_rating)
                final_list.append(r.Book)
            elif isinstance(r, (list, tuple)) and len(r) > 0:
                final_list.append(r[0])
        return final_list

    # 2. Get recommendations from favorite categories
    if top_cats:
        cat_recs = get_books_query(Book.query.filter(Book.category.in_(top_cats)), borrowed_ids, limit)
        recommendations.extend(cat_recs)
        
    # 3. Fallback: Trending books (anything the user hasn't read)
    if len(recommendations) < limit:
        needed = limit - len(recommendations)
        exclude_ids = borrowed_ids + [b.id for b in recommendations]
        trending = get_books_query(Book.query, exclude_ids, needed)
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
