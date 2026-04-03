from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.forms import RegistrationForm, LoginForm
from app import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """Landing page — show role selection or redirect if already logged in."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    return render_template('auth/landing.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle student registration."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            roll_number=form.roll_number.data.strip(),
            phone=form.phone.data.strip(),
            division=form.division.data.strip(),
            department=form.department.data,
            semester=form.semester.data,
            role='user',
            status='active',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.student_login'))

    return render_template('auth/register.html', form=form)


# ── Kept for backwards-compat & Flask-Login redirect ─────────────
@auth_bp.route('/login')
def login():
    """Default login — redirect to landing page."""
    return redirect(url_for('auth.index'))


# ── Student Login ────────────────────────────────────────────────
@auth_bp.route('/student-login', methods=['GET', 'POST'])
def student_login():
    """Handle student (member) login."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/student_login.html', form=form)

        if user.role and user.role.strip().lower() == 'admin':
            flash('Admin accounts must use the Admin login page.', 'warning')
            return render_template('auth/student_login.html', form=form)

        if user.status == 'blocked':
            flash('Your account has been blocked. Please contact the administrator.', 'danger')
            return render_template('auth/student_login.html', form=form)

        login_user(user, remember=True)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('user.dashboard'))

    return render_template('auth/student_login.html', form=form)


# ── Admin Login ──────────────────────────────────────────────────
@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Handle admin (librarian) login."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/admin_login.html', form=form)

        if not user.role or user.role.strip().lower() != 'admin':
            flash('This login is for administrators only.', 'warning')
            return render_template('auth/admin_login.html', form=form)

        login_user(user, remember=True)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))
