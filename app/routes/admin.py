from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.forms import BookForm, IssueBookForm, ReturnBookForm, EditDueDateForm, AdminProfileForm
from datetime import datetime
from app.models import User, Book, IssuedBook, Message, BookRequest
from app.services import book_service, issue_service
from app import db, bcrypt

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def before_request():
    """Ensure all admin routes require authentication and update online heartbeat."""
    from datetime import datetime
    if current_user.is_authenticated:
        current_user.last_active_at = datetime.utcnow()
        db.session.commit()


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
    """List all books with optional search."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    
    pagination = book_service.search_books(query=search_query, page=page, per_page=15)
    
    # Calculate sum of all copies for the header
    from sqlalchemy import func
    total_copies_sum = db.session.query(func.sum(Book.total_copies)).scalar() or 0
    
    return render_template('admin/books.html', 
                         pagination=pagination, 
                         search_query=search_query,
                         total_copies_count=int(total_copies_sum))


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    """Add a new book."""
    form = BookForm()
    if form.validate_on_submit():
        try:
            image_file = form.cover_image.data if form.cover_image.data and form.cover_image.data.filename else None
            book_service.create_book(
                title=form.title.data,
                author=form.author.data,
                category=form.category.data,
                publication=form.publication.data,
                total_copies=form.total_copies.data,
                access_number=form.access_number.data,
                cover_image=image_file
            )
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.books'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while handling the book cover API or database: {e}", 'danger')
    return render_template('admin/book_form.html', form=form, title='Add Book')


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    """Edit an existing book."""
    book = book_service.get_book_by_id(book_id)
    form = BookForm(obj=book)
    if form.validate_on_submit():
        try:
            image_file = form.cover_image.data if form.cover_image.data and form.cover_image.data.filename else None
            book_service.update_book(
                book_id=book_id,
                title=form.title.data,
                author=form.author.data,
                category=form.category.data,
                publication=form.publication.data,
                total_copies=form.total_copies.data,
                access_number=form.access_number.data,
                cover_image=image_file
            )
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.books'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while handling the book cover API or database: {e}", 'danger')
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
    """List all members with optional search."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    
    query = User.query.filter_by(role='user')
    
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.roll_number.ilike(search_term)
            )
        )
        
    pagination = query.order_by(
        User.created_at.desc()
    ).paginate(page=page, per_page=15, error_out=False)
    
    return render_template('admin/users.html', pagination=pagination, search_query=search_query)


@admin_bp.route('/users/toggle-status/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Block or unblock a user."""
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot modify status of an admin account.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.status = 'blocked' if user.status == 'active' else 'active'
    db.session.commit()
    flash(f'Member {user.name} has been {user.status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Permanently delete a user and their associated history."""
    user = User.query.get_or_404(user_id)
    
    if user.role == 'admin':
        flash("Admin accounts cannot be deleted here.", "danger")
        return redirect(url_for('admin.users'))

    # Crucial safety check: Don't let users with active books be deleted
    active_issues = IssuedBook.query.filter(
        IssuedBook.user_id == user_id, 
        IssuedBook.status.in_(['issued', 'overdue'])
    ).count()
    
    if active_issues > 0:
        flash(f"Cannot delete member. {user.name} currently has {active_issues} books in their possession. Please return or resolve these books first.", "danger")
        return redirect(url_for('admin.users'))

    # Manual cleanup for relationships without automatic cascades
    Message.query.filter((Message.sender_id == user.id) | (Message.receiver_id == user.id)).delete()
    
    # Delete issue history (cannot set to NULL because user_id is mandatory)
    IssuedBook.query.filter_by(user_id=user.id).delete()

    # Database handles saved_books, reviews, book_requests, push_subscriptions via cascades
    db.session.delete(user)
    db.session.commit()
    
    flash(f"Member '{user.name}' and all their data have been permanently deleted.", "success")
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
    # Get available books for the dropdown
    available_books = Book.query.filter(Book.available_copies > 0).order_by(Book.title).all()
    form.book_id.choices = [
        (b.id, f'[{b.access_number}] {b.title} — {b.author} (Available: {b.available_copies})' if b.access_number else f'{b.title} — {b.author} (Available: {b.available_copies})')
        for b in available_books
    ]
    
    # Map book_id to list of available BookCopy dicts for frontend dynamic dropdown
    copies_map = {}
    for b in available_books:
        copies = [{'id': c.id, 'access_number': c.access_number} for c in b.copies.filter_by(status='available').all()]
        if copies:
            copies_map[b.id] = copies

    if form.validate_on_submit():
        copy_id_str = request.form.get('copy_id')
        copy_id = int(copy_id_str) if copy_id_str and copy_id_str.isdigit() else None
        try:
            issue_service.issue_book(form.user_id.data, form.book_id.data, copy_id=copy_id, days=form.issue_days.data)
            flash('Book issued successfully!', 'success')
            return redirect(url_for('admin.issued_books'))
        except ValueError as e:
            flash(str(e), 'danger')

    return render_template('admin/issue_book.html', form=form, available_books=available_books, copies_map=copies_map)


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


@admin_bp.route('/issued/clear_all', methods=['POST'])
@admin_required
def clear_all_issues():
    """Danger: Clear issued books history within a date range."""
    from datetime import datetime, timedelta

    start_str = request.form.get('start_date', '')
    end_str = request.form.get('end_date', '')
    only_returned = request.form.get('only_returned') == '1'

    # Validate dates
    if not start_str or not end_str:
        flash('Please select both a start and end date.', 'danger')
        return redirect(url_for('admin.issued_books'))

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1)  # Include end date fully
    except ValueError:
        flash('Invalid date format. Please use the date picker.', 'danger')
        return redirect(url_for('admin.issued_books'))

    if end_date < start_date:
        flash('End date cannot be before start date.', 'danger')
        return redirect(url_for('admin.issued_books'))

    try:
        # Build query with date filter
        query = IssuedBook.query.filter(
            IssuedBook.issue_date >= start_date,
            IssuedBook.issue_date < end_date
        )

        # If "only returned" is checked, skip active/overdue issues
        if only_returned:
            query = query.filter(IssuedBook.status == 'returned')

        records = query.all()
        count = len(records)

        for record in records:
            # If the book is still "out", restore inventory before deleting
            if record.status in ['issued', 'overdue']:
                if record.book:
                    record.book.available_copies += 1
                if record.copy:
                    record.copy.status = 'available'
            db.session.delete(record)

        db.session.commit()

        date_range = f"{start_str} to {end_str}"
        scope = "returned" if only_returned else "all"
        flash(f'Successfully purged {count} {scope} records from {date_range}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing records: {str(e)}', 'danger')

    return redirect(url_for('admin.issued_books'))


@admin_bp.route('/system/resync-inventory', methods=['POST'])
@admin_required
def resync_inventory():
    """Emergency Tool: Resync all physical copies and available counts."""
    try:
        # 1. Reset all physical copies to available
        from app.models import BookCopy, Book
        BookCopy.query.update({BookCopy.status: 'available'})
        
        # 2. Recalculate Book available/total copies based on physical records
        all_books = Book.query.all()
        for book in all_books:
            count = BookCopy.query.filter_by(book_id=book.id).count()
            book.total_copies = count
            book.available_copies = count
            
        db.session.commit()
        flash('System Resync Successful: All books are now marked as available.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error during resync: {str(e)}', 'danger')
        
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/resolve/<int:issue_id>', methods=['POST'])
@admin_required
def resolve_lost_damaged(issue_id):
    """Process a book marked as lost or damaged."""
    issue = IssuedBook.query.get_or_404(issue_id)
    if issue.status == 'returned':
        flash('Cannot resolve a book that is already returned.', 'danger')
        return redirect(url_for('admin.issued_books'))
        
    resolution_type = request.form.get('resolution_type')
    fine_amount_str = request.form.get('fine_amount', '0')
    
    try:
        fine_amount = float(fine_amount_str)
    
    # If the book is completely lost, it permanently leaves inventory
    if resolution_type == 'lost':
        if book.total_copies > 0:
            book.total_copies -= 1
        # Mark the physical copy as lost (or delete it)
        if issue.copy:
            issue.copy.status = 'lost'
        issue.status = 'lost'
        flash_msg = f"Book officially marked as LOST. Total inventory reduced by 1. ₹{fine_amount} fine applied to {issue.user.name}."
    else:
        # If it's just damaged but still in the library's possession
        if book.available_copies < book.total_copies:
            book.available_copies += 1
        # Return the copy back to available
        if issue.copy:
            issue.copy.status = 'available'
        issue.status = 'damaged'
        flash_msg = f"Book marked as DAMAGED. Returned to inventory. ₹{fine_amount} fine applied to {issue.user.name}."
        
    issue.return_date = datetime.utcnow()
    issue.fine_amount = fine_amount
    issue.fine_paid = False if fine_amount > 0 else True
    
    db.session.commit()
    flash(flash_msg, 'warning')
    return redirect(url_for('admin.issued_books'))

@admin_bp.route('/fines')
@admin_required
def fines():
    """View students with outstanding fines from lost/damaged books."""
    search_query = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)

    query = IssuedBook.query.filter(IssuedBook.fine_amount > 0, IssuedBook.fine_paid == False)
    
    if search_query:
        search_term = f"%{search_query}%"
        query = query.join(User).filter(
            db.or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.roll_number.ilike(search_term),
                IssuedBook.issue_code.ilike(search_term)
            )
        )
        
    pagination = query.order_by(IssuedBook.return_date.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/fines.html', pagination=pagination, search_query=search_query)


@admin_bp.route('/fines/clear/<int:issue_id>', methods=['POST'])
@admin_required
def clear_fine(issue_id):
    """Mark a student's fine as paid, unflagging their account."""
    issue = IssuedBook.query.get_or_404(issue_id)
    if issue.fine_paid:
        flash("This fine is already marked as paid.", "info")
        return redirect(url_for('admin.fines'))
        
    issue.fine_paid = True
    db.session.commit()
    flash(f'Successfully cleared ₹{issue.fine_amount} fine for {issue.user.name}. Account unlocked.', 'success')
    return redirect(url_for('admin.fines'))


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
            if issued.status == 'overdue' and new_date > datetime.utcnow():
                issued.status = 'issued'
            elif issued.status == 'issued' and new_date < datetime.utcnow():
                issued.status = 'overdue'
            db.session.commit()
            
            # Send Push Notification to Student
            from app.services.issue_service import send_push_notification
            send_push_notification(
                user_id=issued.user_id,
                title="📚 Due Date Extended!",
                body=f"The Librarian has extended your due date for '{issued.book.title}' to {new_date.strftime('%b %d, %Y')}.",
                url="/user/my-books"
            )
            
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
    from flask import jsonify

    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format.'}), 400

    data = request.json
    
    # Check if we are receiving raw qr_data (old flow) or direct fields (new flow)
    if 'qr_data' in data:
        import json as json_lib
        raw_data = data.get('qr_data', '').strip()
        
        title = author = category = ''
        copies = 1

        # Try JSON format
        try:
            parsed = json_lib.loads(raw_data)
            if isinstance(parsed, dict):
                title = parsed.get('title', parsed.get('Title', '')).strip()
                author = parsed.get('author', parsed.get('Author', '')).strip()
                category = parsed.get('category', parsed.get('Category', 'General')).strip()
                copies = int(parsed.get('copies', parsed.get('Copies', parsed.get('total_copies', 1))))
        except (json_lib.JSONDecodeError, ValueError):
            # Try delimiters...
            if '|' in raw_data: parts = [p.strip() for p in raw_data.split('|')]
            elif ',' in raw_data: parts = [p.strip() for p in raw_data.split(',')]
            elif '\n' in raw_data: parts = [p.strip() for p in raw_data.split('\n')]
            else: parts = [raw_data]

            title = parts[0] if len(parts) > 0 else ''
            author = parts[1] if len(parts) > 1 else 'Unknown'
            category = parts[2] if len(parts) > 2 else 'General'
            try: copies = int(parts[3]) if len(parts) > 3 else 1
            except ValueError: copies = 1
    else:
        # New flow: get fields directly from the modal form
        title = data.get('title', '').strip()
        author = data.get('author', 'Unknown').strip()
        category = data.get('category', 'General').strip()
        try:
            copies = int(data.get('copies', 1))
        except (ValueError, TypeError):
            copies = 1

    if not title:
        return jsonify({'success': False, 'error': 'Book title is required.'}), 400

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
    search_query = request.args.get('q', '').strip()
    issue_service.update_overdue_books()

    pagination = issue_service.get_issued_books(
        status=status_filter if status_filter else None,
        search_query=search_query if search_query else None,
        page=page,
        per_page=20,
    )
    return render_template(
        'admin/issued_books.html',
        pagination=pagination,
        current_status=status_filter,
        search_query=search_query,
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


# ── History ──────────────────────────────────────────────────────────────

@admin_bp.route('/history')
@admin_required
def history():
    """Admin history — all issue/return transactions with optional search."""
    search_query = request.args.get('q', '').strip()
    issue_service.update_overdue_books()
    
    q = IssuedBook.query.join(User).join(Book)
    if search_query:
        search_term = f"%{search_query}%"
        q = q.filter(
            db.or_(
                User.name.ilike(search_term),
                Book.title.ilike(search_term),
                IssuedBook.issue_code.ilike(search_term)
            )
        )
        
    all_issues = q.order_by(IssuedBook.issue_date.desc()).all()
    
    # Calculate stats based on the unfiltered totals to maintain dashboard accuracy
    total_query_all = IssuedBook.query.all()
    total = len(total_query_all)
    active = sum(1 for i in total_query_all if i.status in ('issued', 'overdue'))
    returned = sum(1 for i in total_query_all if i.status == 'returned')
    overdue = sum(1 for i in total_query_all if i.status == 'overdue')
    
    return render_template('admin/history.html', history=all_issues,
                           total=total, active=active, returned=returned, overdue=overdue, search_query=search_query)


@admin_bp.route('/export/issues')
@admin_required
def export_issues():
    """Export issued/returned book records to CSV (opens in Excel)."""
    import csv
    from io import StringIO
    from datetime import timedelta

    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '').strip()
    start_str = request.args.get('start_date', '')
    end_str = request.args.get('end_date', '')

    issue_service.update_overdue_books()

    q = IssuedBook.query.join(User).join(Book)

    # Date range filter
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(
                IssuedBook.issue_date >= start_date,
                IssuedBook.issue_date < end_date
            )
        except ValueError:
            pass  # Silently ignore bad dates and export all

    if status_filter == 'overdue':
        q = q.filter(IssuedBook.status == 'overdue')
    elif status_filter in ('issued', 'returned', 'lost', 'damaged'):
        q = q.filter(IssuedBook.status == status_filter)

    if search_query:
        term = f"%{search_query}%"
        q = q.filter(
            db.or_(
                User.name.ilike(term),
                User.roll_number.ilike(term),
                Book.title.ilike(term),
                IssuedBook.issue_code.ilike(term)
            )
        )

    records = q.order_by(IssuedBook.issue_date.desc()).all()

    headers = [
        'Access Number', 'Student Name', 'Roll Number', 'Department',
        'Division', 'Semester', 'Book Title', 'Author',
        'Issue Date', 'Due Date', 'Return Date', 'Status', 'Fine', 'Fine Paid'
    ]

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(headers)

    for r in records:
        writer.writerow([
            r.book.access_number or '',
            r.user.name,
            r.user.roll_number or '',
            r.user.department or '',
            r.user.division or '',
            r.user.semester or '',
            r.book.title,
            r.book.author,
            r.issue_date.strftime('%Y-%m-%d') if r.issue_date else '',
            r.due_date.strftime('%Y-%m-%d') if r.due_date else '',
            r.return_date.strftime('%Y-%m-%d') if r.return_date else '',
            r.status.capitalize(),
            r.fine_amount if r.fine_amount else 0,
            'Yes' if r.fine_paid else ('No' if r.fine_amount and r.fine_amount > 0 else '-'),
        ])

    # Build descriptive filename
    if start_str and end_str:
        filename = f"OLMS_Issues_{start_str}_to_{end_str}.csv"
    else:
        filename = f"OLMS_Issue_History_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"

    return Response(
        si.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


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

    search_query = request.args.get('q', '').strip()

    # Get all students who have exchanged messages with any admin
    query = db.session.query(
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
    )

    if search_query:
        query = query.filter(User.name.ilike(f"%{search_query}%"))

    students = query.group_by(User.id).order_by(func.max(Message.created_at).desc()).all()

    return render_template('admin/chat_inbox.html', students=students, search_query=search_query)


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
            
            # Send Push Notification to Student
            from app.services.issue_service import send_push_notification
            send_push_notification(
                user_id=student_id,
                title="New message from Librarian",
                body=content[:50] + "..." if len(content) > 50 else content,
                url="/user/chat"
            )
            
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


# ── Student Book Requests ────────────────────────────────────────────────

@admin_bp.route('/book-requests')
@admin_required
def book_requests():
    """View all book requests from students."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = BookRequest.query.join(User).order_by(BookRequest.created_at.desc())
    if status_filter:
        query = query.filter(BookRequest.status == status_filter)
        
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/book_requests.html', pagination=pagination, current_status=status_filter)


@admin_bp.route('/book-requests/<int:req_id>/approve', methods=['POST'])
@admin_required
def approve_request(req_id):
    """Mark a book request as approved for purchase."""
    req = BookRequest.query.get_or_404(req_id)
    req.status = 'approved'
    db.session.commit()
    
    from app.services.issue_service import send_push_notification
    send_push_notification(
        user_id=req.user_id,
        title="Book Request Approved",
        body=f"Your request for '{req.title}' has been approved! We are buying it.",
        url="/user/my-requests"
    )
    
    flash(f"Approved request for '{req.title}'.", 'success')
    return redirect(url_for('admin.book_requests'))


@admin_bp.route('/book-requests/<int:req_id>/reject', methods=['POST'])
@admin_required
def reject_request(req_id):
    """Mark a book request as rejected."""
    req = BookRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    db.session.commit()
    
    from app.services.issue_service import send_push_notification
    send_push_notification(
        user_id=req.user_id,
        title="Book Request Update",
        body=f"Unfortunately, your request for '{req.title}' was not approved at this time.",
        url="/user/my-requests"
    )
    
    flash(f"Rejected request for '{req.title}'.", 'info')
    return redirect(url_for('admin.book_requests'))


@admin_bp.route('/book-requests/<int:req_id>/purchased', methods=['POST'])
@admin_required
def purchase_request(req_id):
    """Mark a book request as formally purchased and available."""
    req = BookRequest.query.get_or_404(req_id)
    req.status = 'purchased'
    db.session.commit()
    
    from app.services.issue_service import send_push_notification
    send_push_notification(
        user_id=req.user_id,
        title="Your Book Arrived!",
        body=f"Great news! '{req.title}' has arrived at the library and is ready for checkout.",
        url="/user/my-requests"
    )
    
    flash(f"Marked '{req.title}' as purchased. The student has been notified!", 'success')
    return redirect(url_for('admin.book_requests'))


@admin_bp.route('/test-500')
def test_500():
    """Temporary test route to crash the server and display the 500 Maintenance Mode error page."""
    raise Exception("This is a deliberate test of the 500 Maintenance Screen!")

@admin_bp.route('/chart-preview')
def chart_preview():
    """Renders the hardcoded sandbox preview of the Chart.js dashboard features."""
    return render_template('admin/chart_demo.html')


