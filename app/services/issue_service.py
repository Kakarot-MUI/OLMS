from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Book, IssuedBook, User


def issue_book(user_id, book_id, copy_id=None, days=None):
    """Issue a specific copy of a book to a user with transactional safety."""
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'
    if user.status != 'active':
        return False, 'This user account is blocked.'

    book = Book.query.get(book_id)
    if not book:
        return False, "Book not found."
        
    # Check if user is flagged for unpaid fines
    if user.is_flagged:
        raise ValueError(f"Account locked due to unpaid fines of ₹{user.total_unpaid_fines}. Please clear debts before borrowing.")

    if book.available_copies <= 0:
        return False, "No copies of this book are currently available."

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
        # Mark copy as issued if we explicitly have one
        from app.models import BookCopy
        copy = None
        if copy_id:
            copy = BookCopy.query.get(copy_id)
            if copy and copy.status == 'available':
                copy.status = 'issued'
        else:
            copy = BookCopy.query.filter_by(book_id=book_id, status='available').first()
            if copy:
                copy.status = 'issued'
                copy_id = copy.id

        issued_book = IssuedBook(
            issue_code=IssuedBook.generate_issue_code(),
            user_id=user_id,
            book_id=book_id,
            copy_id=copy_id if copy else None,
            issue_date=now,
            due_date=now + timedelta(days=days),
            status='issued',
        )
        book.available_copies -= 1
        db.session.add(issued_book)
        db.session.commit()
        
        # Notify the student that the book was issued
        send_push_notification(
            user_id=user_id,
            title="📖 Book Issued!",
            body=f"'{book.title}' has been successfully issued to you. Happy reading!",
            url="/user/my-books"
        )
        
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
        
        # Free up the specific copy
        if issued.copy_id:
            from app.models import BookCopy
            copy = BookCopy.query.get(issued.copy_id)
            if copy:
                copy.status = 'available'
                
        db.session.commit()
        return issued
    except Exception:
        db.session.rollback()
        raise


def update_overdue_books():
    """Mark all overdue books that have passed their due date, and send Due Soon notifications."""
    now = datetime.utcnow()
    
    # 1. Handle strictly overdue books
    overdue_records = IssuedBook.query.filter(
        IssuedBook.status == 'issued',
        IssuedBook.due_date < now,
    ).all()

    for record in overdue_records:
        record.status = 'overdue'

    # 2. Handle books due in exactly 2 days or less (and not already notified)
    warning_deadline = now + timedelta(days=2)
    due_soon_records = IssuedBook.query.filter(
        IssuedBook.status == 'issued',
        IssuedBook.due_date <= warning_deadline,
        IssuedBook.due_date >= now,
        IssuedBook.notified_due_soon == False
    ).all()
    
    for record in due_soon_records:
        days_left = (record.due_date - now).days
        # Time calculations (e.g. 1 day left vs tomorrow)
        time_text = f"in {days_left} days" if days_left > 1 else "tomorrow" if days_left == 1 else "today"
        
        send_push_notification(
            user_id=record.user_id,
            title="⏳ Book Due Soon!",
            body=f"Reminder: Please return '{record.book.title}' {time_text} to avoid fines.",
            url="/user/my-books"
        )
        record.notified_due_soon = True

    if overdue_records or due_soon_records:
        db.session.commit()

    return len(overdue_records)


def get_issued_books(status=None, search_query=None, page=1, per_page=20):
    """Get issued books with optional status filter and search query."""
    q = IssuedBook.query.join(User).join(Book)

    if status:
        q = q.filter(IssuedBook.status == status)
        
    if search_query:
        search_term = f"%{search_query.strip()}%"
        q = q.filter(
            db.or_(
                User.name.ilike(search_term),
                Book.title.ilike(search_term),
                IssuedBook.issue_code.ilike(search_term)
            )
        )

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
    from sqlalchemy import func

    # Count actual copies of all books
    total_books = db.session.query(func.sum(Book.total_copies)).scalar() or 0
    total_users = User.query.filter_by(role='user').count()
    issued_count = IssuedBook.query.filter_by(status='issued').count()
    overdue_count = IssuedBook.query.filter_by(status='overdue').count()
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(5).all()

    return {
        'total_books': int(total_books),
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
    returned = IssuedBook.query.filter(
        IssuedBook.user_id == user_id,
        IssuedBook.status.in_(['returned', 'lost_replaced', 'damaged_replaced'])
    ).count()
    return {
        'total_borrowed': total,
        'currently_active': active,
        'overdue': overdue,
        'returned': returned,
    }


def send_push_notification(user_id, title, body, url="/"):
    """Send a Web Push Notification to a specific user's registered devices."""
    import json
    from pywebpush import webpush, WebPushException
    from flask import current_app
    from app.models import PushSubscription, db
    
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions:
        return False
        
    vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
    vapid_claims = current_app.config.get('VAPID_CLAIMS')
    vapid_claim_email = current_app.config.get('VAPID_CLAIM_EMAIL')
    
    if not vapid_claims and vapid_claim_email:
        vapid_claims = {"sub": f"mailto:{vapid_claim_email}"}
    
    if not vapid_private_key or not vapid_claims:
        current_app.logger.error("VAPID config missing. Cannot send push.")
        return False
        
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": "/static/icon-512.png"
    })
    
    success_count = 0
    for sub in subscriptions:
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth
            }
        }
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims
            )
            success_count += 1
        except WebPushException as ex:
            current_app.logger.error(f"Push failed: {repr(ex)}")
            # If the subscription is expired/unsubscribed (410 Gone), remove it
            if ex.response and ex.response.status_code in [404, 410]:
                db.session.delete(sub)
                db.session.commit()
                
    return success_count > 0
