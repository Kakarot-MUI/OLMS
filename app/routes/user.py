from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.decorators import active_required
from app.services import book_service, issue_service
from app.models import IssuedBook, User, Message
from flask import current_app
from app import db
from sqlalchemy import or_, and_

user_bp = Blueprint('user', __name__)


@user_bp.before_request
@login_required
def before_request():
    """Ensure all user routes require login."""
    pass


@user_bp.route('/dashboard')
@active_required
def dashboard():
    """User dashboard showing their issued books."""
    issue_service.update_overdue_books()
    my_books = issue_service.get_user_issued_books(current_user.id)
    active_books = [b for b in my_books if b.status in ('issued', 'overdue')]
    returned_books = [b for b in my_books if b.status == 'returned']
    return render_template(
        'user/dashboard.html',
        active_books=active_books,
        returned_books=returned_books,
    )


@user_bp.route('/search')
@active_required
def search():
    """Search and browse books."""
    query = request.args.get('query', '', type=str)
    category = request.args.get('category', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('BOOKS_PER_PAGE', 12)

    categories = book_service.get_all_categories()
    pagination = book_service.search_books(
        query=query if query else None,
        category=category if category else None,
        page=page,
        per_page=per_page,
    )

    return render_template(
        'user/search.html',
        pagination=pagination,
        categories=categories,
        current_query=query,
        current_category=category,
    )


@user_bp.route('/book/<int:book_id>')
@active_required
def book_detail(book_id):
    """View book details."""
    book = book_service.get_book_by_id(book_id)

    # Check if user currently has this book issued
    user_has_book = IssuedBook.query.filter_by(
        user_id=current_user.id,
        book_id=book_id,
        status='issued',
    ).first() is not None

    return render_template(
        'user/book_detail.html',
        book=book,
        user_has_book=user_has_book,
    )


@user_bp.route('/my-books')
@active_required
def my_books():
    """View user's issued books history."""
    issue_service.update_overdue_books()
    my_books = issue_service.get_user_issued_books(current_user.id)
    return render_template('user/my_books.html', issued_books=my_books)


# ── Chat ─────────────────────────────────────────────────────────────────

@user_bp.route('/chat', methods=['GET', 'POST'])
@active_required
def chat():
    """Student chat with admin."""
    # Find the admin to chat with
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        flash('No admin available for chat.', 'warning')
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        content = request.form.get('message', '').strip()
        if content:
            msg = Message(
                sender_id=current_user.id,
                receiver_id=admin.id,
                content=content,
            )
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('user.chat'))

    # Mark messages from admin as read
    Message.query.filter_by(
        sender_id=admin.id, receiver_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()

    # Get all messages between student and admin
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == admin.id),
            and_(Message.sender_id == admin.id, Message.receiver_id == current_user.id),
        )
    ).order_by(Message.created_at.asc()).all()

    return render_template('user/chat.html', messages=messages, admin=admin)
