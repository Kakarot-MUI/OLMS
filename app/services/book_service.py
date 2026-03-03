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
    """Delete a book if no copies are currently issued."""
    book = Book.query.get_or_404(book_id)
    issued_count = book.total_copies - book.available_copies
    if issued_count > 0:
        raise ValueError(
            f'Cannot delete this book. {issued_count} copies are currently issued.'
        )
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
