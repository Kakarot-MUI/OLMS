from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.forms import BookForm, IssueBookForm, ReturnBookForm, EditDueDateForm, AdminProfileForm
from datetime import datetime
from app.models import User, Book, IssuedBook, Message
from app.services import book_service, issue_service
from app import db, bcrypt

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def before_request():
    """Ensure all admin routes require authentication."""
    pass


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics."""
    issue_service.update_overdue_books()
    stats = issue_service.get_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats)


# ── Book Management ──────────────────────────────────────────────────────

@admin_bp.route('/books')
@admin_required
def books():
    """List all books."""
    page = request.args.get('page', 1, type=int)
    pagination = book_service.search_books(page=page, per_page=15)
    return render_template('admin/books.html', pagination=pagination)


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    """Add a new book."""
    form = BookForm()
    if form.validate_on_submit():
        book_service.create_book(
            title=form.title.data,
            author=form.author.data,
            category=form.category.data,
            total_copies=form.total_copies.data,
        )
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin.books'))
    return render_template('admin/book_form.html', form=form, title='Add Book')


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    """Edit an existing book."""
    book = book_service.get_book_by_id(book_id)
    form = BookForm(obj=book)
    if form.validate_on_submit():
        try:
            book_service.update_book(
                book_id=book_id,
                title=form.title.data,
                author=form.author.data,
                category=form.category.data,
                total_copies=form.total_copies.data,
            )
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.books'))
        except ValueError as e:
            flash(str(e), 'danger')
    return render_template('admin/book_form.html', form=form, title='Edit Book', book=book)


@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    """Delete a book."""
    try:
        book_service.delete_book(book_id)
        flash('Book deleted successfully!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.books'))


# ── User Management ─────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    """List all members."""
    page = request.args.get('page', 1, type=int)
    pagination = User.query.filter_by(role='user').order_by(
        User.created_at.desc()
    ).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/users.html', pagination=pagination)


@admin_bp.route('/users/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Block or unblock a user."""
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot modify admin accounts.', 'danger')
        return redirect(url_for('admin.users'))

    user.status = 'blocked' if user.status == 'active' else 'active'
    db.session.commit()
    status_text = 'blocked' if user.status == 'blocked' else 'activated'
    flash(f'User {user.name} has been {status_text}.', 'success')
    return redirect(url_for('admin.users'))


# ── Issue / Return ───────────────────────────────────────────────────────

@admin_bp.route('/issue', methods=['GET', 'POST'])
@admin_required
def issue_book():
    """Issue a book to a user."""
    form = IssueBookForm()
    # Populate select fields
    form.user_id.choices = [
        (u.id, f'{u.name} ({u.email})')
        for u in User.query.filter_by(role='user', status='active').order_by(User.name).all()
    ]
    form.book_id.choices = [
        (b.id, f'{b.title} — {b.author} (Available: {b.available_copies})')
        for b in Book.query.filter(Book.available_copies > 0).order_by(Book.title).all()
    ]

    if form.validate_on_submit():
        try:
            issue_service.issue_book(form.user_id.data, form.book_id.data, days=form.issue_days.data)
            flash('Book issued successfully!', 'success')
            return redirect(url_for('admin.issued_books'))
        except ValueError as e:
            flash(str(e), 'danger')

    return render_template('admin/issue_book.html', form=form)


@admin_bp.route('/return/<int:issue_id>', methods=['POST'])
@admin_required
def return_book(issue_id):
    """Process a book return."""
    try:
        issue_service.return_book(issue_id)
        flash('Book returned successfully!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.issued_books'))


@admin_bp.route('/edit-due-date/<int:issue_id>', methods=['GET', 'POST'])
@admin_required
def edit_due_date(issue_id):
    """Edit the due date of an issued book."""
    issued = IssuedBook.query.get_or_404(issue_id)
    if issued.status == 'returned':
        flash('Cannot edit due date of a returned book.', 'danger')
        return redirect(url_for('admin.issued_books'))

    form = EditDueDateForm()
    if form.validate_on_submit():
        try:
            new_date = datetime.strptime(form.due_date.data, '%Y-%m-%d')
            issued.due_date = new_date
            # If was overdue but new date is in future, reset to issued
            if issued.status == 'overdue' and new_date > datetime.utcnow():
                issued.status = 'issued'
            elif issued.status == 'issued' and new_date < datetime.utcnow():
                issued.status = 'overdue'
            db.session.commit()
            flash(f'Due date updated to {new_date.strftime("%b %d, %Y")}!', 'success')
            return redirect(url_for('admin.issued_books'))
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')

    return render_template('admin/edit_due_date.html', issued=issued, form=form)


# ── QR Code Scanner ──────────────────────────────────────────────────────

@admin_bp.route('/scan')
@admin_required
def scan_book():
    """QR code scanner page."""
    return render_template('admin/scan_book.html')


@admin_bp.route('/scan/add', methods=['POST'])
@admin_required
def scan_book_api():
    """API endpoint to add a book from scanned QR data."""
    import json as json_lib
    from flask import jsonify

    raw_data = request.json.get('qr_data', '').strip() if request.is_json else ''
    if not raw_data:
        return jsonify({'success': False, 'error': 'No QR data received.'}), 400

    title = author = category = ''
    copies = 1

    # Try JSON format: {"title":"...","author":"...","category":"...","copies":N}
    try:
        parsed = json_lib.loads(raw_data)
        if isinstance(parsed, dict):
            title = parsed.get('title', parsed.get('Title', '')).strip()
            author = parsed.get('author', parsed.get('Author', '')).strip()
            category = parsed.get('category', parsed.get('Category', 'General')).strip()
            copies = int(parsed.get('copies', parsed.get('Copies', parsed.get('total_copies', 1))))
    except (json_lib.JSONDecodeError, ValueError):
        # Try pipe-delimited: Title|Author|Category|Copies
        if '|' in raw_data:
            parts = [p.strip() for p in raw_data.split('|')]
        # Try comma-delimited: Title,Author,Category,Copies
        elif ',' in raw_data:
            parts = [p.strip() for p in raw_data.split(',')]
        # Try newline-delimited
        elif '\n' in raw_data:
            parts = [p.strip() for p in raw_data.split('\n')]
        else:
            # Single value — treat as title
            parts = [raw_data]

        title = parts[0] if len(parts) > 0 else ''
        author = parts[1] if len(parts) > 1 else 'Unknown'
        category = parts[2] if len(parts) > 2 else 'General'
        try:
            copies = int(parts[3]) if len(parts) > 3 else 1
        except ValueError:
            copies = 1

    if not title:
        return jsonify({'success': False, 'error': 'Could not extract book title from QR data.'}), 400

    # Check if book already exists
    existing = Book.query.filter_by(title=title, author=author).first()
    if existing:
        return jsonify({
            'success': False,
            'error': f'Book "{title}" by {author} already exists (ID: {existing.id}).',
            'existing_id': existing.id,
        }), 409

    book = Book(
        title=title,
        author=author,
        category=category or 'General',
        total_copies=max(1, copies),
        available_copies=max(1, copies),
    )
    db.session.add(book)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Book "{title}" added successfully!',
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'total_copies': book.total_copies,
        }
    })


# ── Reports ──────────────────────────────────────────────────────────────

@admin_bp.route('/issued')
@admin_required
def issued_books():
    """View all issued books."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    issue_service.update_overdue_books()

    pagination = issue_service.get_issued_books(
        status=status_filter if status_filter else None,
        page=page,
        per_page=20,
    )
    return render_template(
        'admin/issued_books.html',
        pagination=pagination,
        current_status=status_filter,
    )


@admin_bp.route('/reports')
@admin_required
def reports():
    """Reports page with overdue and issue stats."""
    issue_service.update_overdue_books()
    stats = issue_service.get_dashboard_stats()

    overdue_books = IssuedBook.query.filter_by(status='overdue').join(User).join(Book).all()
    issued_books = IssuedBook.query.filter_by(status='issued').join(User).join(Book).all()

    return render_template(
        'admin/reports.html',
        stats=stats,
        overdue_books=overdue_books,
        issued_books=issued_books,
    )


# ── Lookup Issue Code ────────────────────────────────────────────────────

@admin_bp.route('/lookup', methods=['GET', 'POST'])
@admin_required
def lookup_code():
    """Lookup student details by issue code."""
    result = None
    code = ''
    error = None

    if request.method == 'POST':
        code = request.form.get('issue_code', '').strip().upper()
        if not code:
            error = 'Please enter an issue code.'
        else:
            result = IssuedBook.query.filter_by(issue_code=code).first()
            if not result:
                error = f'No record found for code "{code}".'

    return render_template('admin/lookup.html', result=result, code=code, error=error)


# ── Profile ──────────────────────────────────────────────────────────────

@admin_bp.route('/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    """Admin profile page — view and edit."""
    form = AdminProfileForm(obj=current_user)
    stats = issue_service.get_dashboard_stats()

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()

        # Handle optional password change
        if form.new_password.data:
            if not form.current_password.data:
                flash('Please enter your current password to change it.', 'warning')
                return render_template('admin/profile.html', form=form, stats=stats)
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('admin/profile.html', form=form, stats=stats)
            current_user.set_password(form.new_password.data)
            flash('Password updated successfully!', 'success')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin.admin_profile'))

    return render_template('admin/profile.html', form=form, stats=stats)


# ── Chat ─────────────────────────────────────────────────────────────────

@admin_bp.route('/chat')
@admin_required
def chat_inbox():
    """Admin chat inbox — list all student conversations."""
    from flask_login import current_user
    from sqlalchemy import func, case, or_, and_

    # Get all students who have exchanged messages with any admin
    students = db.session.query(
        User,
        func.max(Message.created_at).label('last_msg_time'),
        func.sum(case(
            (and_(Message.receiver_id == current_user.id, Message.is_read == False), 1),
            else_=0
        )).label('unread_count')
    ).join(
        Message, or_(Message.sender_id == User.id, Message.receiver_id == User.id)
    ).filter(
        User.role == 'user',
        or_(Message.sender_id == current_user.id, Message.receiver_id == current_user.id)
    ).group_by(User.id).order_by(func.max(Message.created_at).desc()).all()

    return render_template('admin/chat_inbox.html', students=students)


@admin_bp.route('/chat/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def chat_with_student(student_id):
    """Chat with a specific student."""
    from flask_login import current_user
    from flask import jsonify
    from sqlalchemy import or_, and_

    student = User.query.get_or_404(student_id)
    if student.role != 'user':
        flash('Invalid student.', 'danger')
        return redirect(url_for('admin.chat_inbox'))

    if request.method == 'POST':
        content = request.form.get('message', '').strip()
        if content:
            msg = Message(
                sender_id=current_user.id,
                receiver_id=student_id,
                content=content,
            )
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('admin.chat_with_student', student_id=student_id))

    # Mark messages from this student as read
    Message.query.filter_by(
        sender_id=student_id, receiver_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()

    # Get all messages between admin and student
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == student_id),
            and_(Message.sender_id == student_id, Message.receiver_id == current_user.id),
        )
    ).order_by(Message.created_at.asc()).all()

    return render_template('admin/chat.html', student=student, messages=messages)
