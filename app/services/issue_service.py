from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Book, IssuedBook, User


def issue_book(user_id, book_id, days=None):
    """Issue a book to a user with transactional safety."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError('User not found.')
    if user.status != 'active':
        raise ValueError('This user account is blocked.')

    book = Book.query.get(book_id)
    if not book:
        raise ValueError('Book not found.')
    if book.available_copies <= 0:
        raise ValueError('No copies of this book are currently available.')

    # Check if user already has this book issued
    existing = IssuedBook.query.filter_by(
        user_id=user_id, book_id=book_id, status='issued'
    ).first()
    if existing:
        raise ValueError('This user already has a copy of this book issued.')

    if days is None:
        days = current_app.config.get('ISSUE_DURATION_DAYS', 14)
    now = datetime.utcnow()

    try:
        issued_book = IssuedBook(
            issue_code=IssuedBook.generate_issue_code(),
            user_id=user_id,
            book_id=book_id,
            issue_date=now,
            due_date=now + timedelta(days=days),
            status='issued',
        )
        book.available_copies -= 1
        db.session.add(issued_book)
        db.session.commit()
        return issued_book
    except Exception:
        db.session.rollback()
        raise


def return_book(issue_id):
    """Process a book return with transactional safety."""
    issued = IssuedBook.query.get(issue_id)
    if not issued:
        raise ValueError('Issued book record not found.')
    if issued.status == 'returned':
        raise ValueError('This book has already been returned.')

    try:
        issued.return_date = datetime.utcnow()
        issued.status = 'returned'
        issued.book.available_copies += 1
        db.session.commit()
        return issued
    except Exception:
        db.session.rollback()
        raise


def update_overdue_books():
    """Mark all overdue books that have passed their due date."""
    now = datetime.utcnow()
    overdue_records = IssuedBook.query.filter(
        IssuedBook.status == 'issued',
        IssuedBook.due_date < now,
    ).all()

    for record in overdue_records:
        record.status = 'overdue'

    if overdue_records:
        db.session.commit()

    return len(overdue_records)


def get_issued_books(status=None, page=1, per_page=20):
    """Get issued books with optional status filter."""
    q = IssuedBook.query.join(User).join(Book)

    if status:
        q = q.filter(IssuedBook.status == status)

    q = q.order_by(IssuedBook.issue_date.desc())
    return q.paginate(page=page, per_page=per_page, error_out=False)


def get_user_issued_books(user_id):
    """Get all issued books for a specific user."""
    return IssuedBook.query.filter_by(user_id=user_id).order_by(
        IssuedBook.issue_date.desc()
    ).all()


def get_dashboard_stats():
    """Get statistics for the admin dashboard."""
    from app.models import User, Book, IssuedBook

    total_books = Book.query.count()
    total_users = User.query.filter_by(role='user').count()
    issued_count = IssuedBook.query.filter_by(status='issued').count()
    overdue_count = IssuedBook.query.filter_by(status='overdue').count()
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(5).all()

    return {
        'total_books': total_books,
        'total_users': total_users,
        'issued_count': issued_count,
        'overdue_count': overdue_count,
        'recent_books': recent_books,
    }


def get_due_date_status(due_date):
    """Return urgency level for a due date."""
    now = datetime.utcnow()
    delta = (due_date - now).days
    if delta < 0:
        return 'overdue'
    elif delta <= 2:
        return 'urgent'
    elif delta <= 5:
        return 'upcoming'
    return 'safe'


def get_days_remaining(due_date):
    """Return days until due date (negative if overdue)."""
    now = datetime.utcnow()
    return (due_date - now).days


def get_user_borrowing_stats(user_id):
    """Get borrowing statistics for a user's profile."""
    total = IssuedBook.query.filter_by(user_id=user_id).count()
    active = IssuedBook.query.filter(
        IssuedBook.user_id == user_id,
        IssuedBook.status.in_(['issued', 'overdue'])
    ).count()
    overdue = IssuedBook.query.filter_by(user_id=user_id, status='overdue').count()
    returned = IssuedBook.query.filter_by(user_id=user_id, status='returned').count()
    return {
        'total_borrowed': total,
        'currently_active': active,
        'overdue': overdue,
        'returned': returned,
    }
