from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.decorators import active_required
from app.services import book_service, issue_service
from app.models import IssuedBook, User, Message, BookRequest
from app.forms import StudentProfileForm
from flask import current_app
from app import db, bcrypt
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

    # Build due date info for active books
    due_date_info = {}
    for book in active_books:
        due_date_info[book.id] = {
            'status': issue_service.get_due_date_status(book.due_date),
            'days': issue_service.get_days_remaining(book.due_date),
        }

    return render_template(
        'user/dashboard.html',
        active_books=active_books,
        returned_books=returned_books,
        due_date_info=due_date_info
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

    from datetime import datetime
    earliest_available = {}
    for book in pagination.items:
        if not book.is_available:
            issue = IssuedBook.query.filter_by(book_id=book.id, status='issued').order_by(IssuedBook.due_date.asc()).first()
            if issue:
                days_left = (issue.due_date.date() - datetime.utcnow().date()).days
                earliest_available[book.id] = days_left

    return render_template(
        'user/search.html',
        pagination=pagination,
        categories=categories,
        current_query=query,
        current_category=category,
        earliest_available=earliest_available,
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
    
    # Check if user has previously borrowed the book (for review eligibility)
    has_borrowed = IssuedBook.query.filter_by(
        user_id=current_user.id,
        book_id=book_id
    ).first() is not None

    is_saved = book_service.is_book_saved(current_user.id, book_id)
    average_rating = book_service.get_book_average_rating(book_id)
    reviews = book_service.get_book_reviews(book_id)
    user_review = book_service.get_user_review_for_book(current_user.id, book_id)

    return render_template(
        'user/book_detail.html',
        book=book,
        user_has_book=user_has_book,
        is_saved=is_saved,
        average_rating=average_rating,
        reviews=reviews,
        user_review=user_review,
        can_review=has_borrowed
    )

# ── Saved Books ─────────────────────────────────────────────────────────

@user_bp.route('/saved-books')
@active_required
def saved_books():
    """View user's saved books."""
    saved = book_service.get_user_saved_books(current_user.id)
    return render_template('user/saved_books.html', saved_books=saved)

@user_bp.route('/book/<int:book_id>/save', methods=['POST'])
@active_required
def save_book(book_id):
    """Save a book for later."""
    book_service.save_book(current_user.id, book_id)
    flash('Book saved to your wishlist.', 'success')
    return redirect(url_for('user.book_detail', book_id=book_id))

@user_bp.route('/book/<int:book_id>/unsave', methods=['POST'])
@active_required
def unsave_book(book_id):
    """Remove a book from saved list."""
    book_service.unsave_book(current_user.id, book_id)
    flash('Book removed from your wishlist.', 'info')
    if request.referrer and 'saved-books' in request.referrer:
        return redirect(url_for('user.saved_books'))
    return redirect(url_for('user.book_detail', book_id=book_id))

# ── Reviews ─────────────────────────────────────────────────────────────

@user_bp.route('/book/<int:book_id>/review', methods=['POST'])
@active_required
def submit_review(book_id):
    """Submit a review for a book."""
    rating = request.form.get('rating', type=int)
    content = request.form.get('content', '').strip()
    
    if not rating or rating < 1 or rating > 5:
        flash('Invalid rating. Please select 1 to 5 stars.', 'danger')
        return redirect(url_for('user.book_detail', book_id=book_id))
        
    has_borrowed = IssuedBook.query.filter_by(
        user_id=current_user.id,
        book_id=book_id
    ).first() is not None
    
    if not has_borrowed:
        flash('You can only review books you have borrowed.', 'warning')
        return redirect(url_for('user.book_detail', book_id=book_id))
        
    book_service.add_review(current_user.id, book_id, rating, content)
    flash('Your review has been saved!', 'success')
    return redirect(url_for('user.book_detail', book_id=book_id))


@user_bp.route('/my-books')
@active_required
def my_books():
    """View user's issued books history."""
    issue_service.update_overdue_books()
    my_books = issue_service.get_user_issued_books(current_user.id)

    # Add due date info for active books
    due_date_info = {}
    for book in my_books:
        if book.status in ('issued', 'overdue'):
            due_date_info[book.id] = {
                'status': issue_service.get_due_date_status(book.due_date),
                'days': issue_service.get_days_remaining(book.due_date),
            }

    return render_template('user/my_books.html', issued_books=my_books, due_date_info=due_date_info)


# ── History ─────────────────────────────────────────────────────────────

@user_bp.route('/history')
@active_required
def history():
    """Student borrowing history — all issued and returned books."""
    issue_service.update_overdue_books()
    all_books = issue_service.get_user_issued_books(current_user.id)
    stats = issue_service.get_user_borrowing_stats(current_user.id)
    return render_template('user/history.html', history=all_books, stats=stats)


# ── Profile ──────────────────────────────────────────────────────────────

@user_bp.route('/profile', methods=['GET', 'POST'])
@active_required
def profile():
    """Student profile page — view and edit."""
    form = StudentProfileForm(obj=current_user)
    stats = issue_service.get_user_borrowing_stats(current_user.id)

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        current_user.division = form.division.data.strip() if form.division.data else None
        current_user.department = form.department.data if form.department.data else None
        current_user.semester = form.semester.data if form.semester.data else None

        # Handle optional password change
        if form.new_password.data:
            if not form.current_password.data:
                flash('Please enter your current password to change it.', 'warning')
                return render_template('user/profile.html', form=form, stats=stats)
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('user/profile.html', form=form, stats=stats)
            current_user.set_password(form.new_password.data)
            flash('Password updated successfully!', 'success')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html', form=form, stats=stats)


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
            
            # Send Push Notification to Admin
            from app.services.issue_service import send_push_notification
            send_push_notification(
                user_id=admin.id,
                title=f"New message from {current_user.name}",
                body=content[:50] + "..." if len(content) > 50 else content,
                url=f"/admin/chat/{current_user.id}"
            )
            
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


# ── Book Requests ────────────────────────────────────────────────────────

@user_bp.route('/request-book', methods=['GET', 'POST'])
@active_required
def request_book():
    """Form for students to request new books."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not title or not author:
            flash('Title and Author are required fields.', 'danger')
            return redirect(url_for('user.request_book'))
            
        new_request = BookRequest(
            user_id=current_user.id,
            title=title,
            author=author,
            reason=reason
        )
        db.session.add(new_request)
        db.session.commit()
        
        # Notify Admin
        from app.services.issue_service import send_push_notification
        admin = User.query.filter_by(role='admin').first()
        if admin:
            send_push_notification(
                user_id=admin.id,
                title="New Book Request",
                body=f"{current_user.name} requested '{title}' by {author}.",
                url="/admin/book-requests"
            )
            
        flash(f'Your request for "{title}" has been submitted successfully!', 'success')
        return redirect(url_for('user.my_requests'))
        
    return render_template('user/request_form.html')


@user_bp.route('/my-requests')
@active_required
def my_requests():
    """View status of student's book requests."""
    page = request.args.get('page', 1, type=int)
    pagination = BookRequest.query.filter_by(user_id=current_user.id).order_by(
        BookRequest.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('user/my_requests.html', pagination=pagination)

