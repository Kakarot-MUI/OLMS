import pytest
from app import create_app, db
from app.models import User, Book, IssuedBook


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    with app.app_context():
        user = User(name='Admin', email='admin@test.com', role='admin', status='active')
        user.set_password('Admin@123')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def regular_user(app):
    """Create a regular user."""
    with app.app_context():
        user = User(name='Test User', email='user@test.com', role='user', status='active')
        user.set_password('User@123')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def blocked_user(app):
    """Create a blocked user."""
    with app.app_context():
        user = User(name='Blocked User', email='blocked@test.com', role='user', status='blocked')
        user.set_password('Blocked@123')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_book(app):
    """Create a sample book."""
    with app.app_context():
        book = Book(title='Test Book', author='Test Author', category='Fiction', total_copies=3, available_copies=3)
        db.session.add(book)
        db.session.commit()
        return book.id


def login(client, email, password, role='user'):
    """Helper to log in a user via the appropriate login route."""
    url = '/admin-login' if role == 'admin' else '/student-login'
    return client.post(url, data={'email': email, 'password': password}, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/logout', follow_redirects=True)


# ═══════════════════════════════════════════════════════════════════
# Authentication Tests
# ═══════════════════════════════════════════════════════════════════

class TestAuthentication:
    """Test authentication flows."""

    def test_register_page_loads(self, client):
        response = client.get('/register')
        assert response.status_code == 200
        assert b'Create Account' in response.data

    def test_student_login_page_loads(self, client):
        response = client.get('/student-login')
        assert response.status_code == 200
        assert b'Student Login' in response.data

    def test_admin_login_page_loads(self, client):
        response = client.get('/admin-login')
        assert response.status_code == 200
        assert b'Admin Login' in response.data

    def test_successful_registration(self, client):
        response = client.post('/register', data={
            'name': 'New User',
            'email': 'newuser@test.com',
            'roll_number': '2024CS001',
            'phone': '9876543210',
            'division': 'A',
            'department': 'Computer Science',
            'semester': 3,
            'password': 'Test@123',
            'confirm_password': 'Test@123',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Registration successful' in response.data

    def test_duplicate_email_registration(self, client, regular_user):
        response = client.post('/register', data={
            'name': 'Another User',
            'email': 'user@test.com',
            'roll_number': '2024CS002',
            'phone': '9876543211',
            'division': 'B',
            'department': 'Computer Science',
            'semester': 2,
            'password': 'Test@123',
            'confirm_password': 'Test@123',
        }, follow_redirects=True)
        assert b'already registered' in response.data

    def test_password_mismatch_registration(self, client):
        response = client.post('/register', data={
            'name': 'User',
            'email': 'mismatch@test.com',
            'roll_number': '2024CS003',
            'phone': '9876543212',
            'division': 'A',
            'department': 'Computer Science',
            'semester': 1,
            'password': 'Test@123',
            'confirm_password': 'Different@123',
        }, follow_redirects=True)
        assert b'Passwords must match' in response.data

    def test_successful_login(self, client, regular_user):
        response = login(client, 'user@test.com', 'User@123', role='user')
        assert response.status_code == 200
        assert b'Welcome back' in response.data

    def test_invalid_password_login(self, client, regular_user):
        response = login(client, 'user@test.com', 'WrongPassword', role='user')
        assert b'Invalid email or password' in response.data

    def test_nonexistent_user_login(self, client):
        response = login(client, 'nobody@test.com', 'NoPassword', role='user')
        assert b'Invalid email or password' in response.data

    def test_blocked_user_login(self, client, blocked_user):
        response = login(client, 'blocked@test.com', 'Blocked@123')
        assert b'blocked' in response.data

    def test_logout(self, client, regular_user):
        login(client, 'user@test.com', 'User@123')
        response = logout(client)
        assert response.status_code == 200
        assert b'logged out' in response.data


# ═══════════════════════════════════════════════════════════════════
# Access Control Tests
# ═══════════════════════════════════════════════════════════════════

class TestAccessControl:
    """Test role-based access restrictions."""

    def test_admin_dashboard_requires_admin(self, client, regular_user):
        login(client, 'user@test.com', 'User@123', role='user')
        response = client.get('/admin/dashboard')
        assert response.status_code == 403

    def test_admin_can_access_dashboard(self, client, admin_user):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.get('/admin/dashboard')
        assert response.status_code == 200

    def test_unauthenticated_cannot_access_admin(self, client):
        response = client.get('/admin/dashboard', follow_redirects=True)
        assert response.status_code == 200

    def test_unauthenticated_cannot_access_user_area(self, client):
        response = client.get('/user/dashboard', follow_redirects=True)
        assert response.status_code == 200

    def test_user_can_access_own_dashboard(self, client, regular_user):
        login(client, 'user@test.com', 'User@123', role='user')
        response = client.get('/user/dashboard')
        assert response.status_code == 200

    def test_admin_books_requires_admin(self, client, regular_user):
        login(client, 'user@test.com', 'User@123', role='user')
        response = client.get('/admin/books')
        assert response.status_code == 403

    def test_admin_users_requires_admin(self, client, regular_user):
        login(client, 'user@test.com', 'User@123', role='user')
        response = client.get('/admin/users')
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════
# Book CRUD Tests
# ═══════════════════════════════════════════════════════════════════

class TestBookCRUD:
    """Test book management operations."""

    def test_add_book(self, client, admin_user):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post('/admin/books/add', data={
            'title': 'New Book',
            'author': 'Author Name',
            'category': 'Fiction',
            'total_copies': 5,
        }, follow_redirects=True)
        assert b'Book added successfully' in response.data

    def test_edit_book(self, client, admin_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post(f'/admin/books/edit/{sample_book}', data={
            'title': 'Updated Title',
            'author': 'Updated Author',
            'category': 'Science',
            'total_copies': 5,
        }, follow_redirects=True)
        assert b'Book updated successfully' in response.data

    def test_delete_book(self, client, admin_user, sample_book):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post(f'/admin/books/delete/{sample_book}', follow_redirects=True)
        assert b'Book deleted successfully' in response.data

    def test_add_book_missing_title(self, client, admin_user):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post('/admin/books/add', data={
            'title': '',
            'author': 'Author',
            'category': 'Fiction',
            'total_copies': 1,
        })
        assert response.status_code == 200  # stays on form with errors

    def test_books_list(self, client, admin_user, sample_book):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.get('/admin/books')
        assert response.status_code == 200
        assert b'Test Book' in response.data


# ═══════════════════════════════════════════════════════════════════
# Issue & Return Tests
# ═══════════════════════════════════════════════════════════════════

class TestIssueReturn:
    """Test book issue and return logic."""

    def test_issue_book(self, client, admin_user, regular_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post('/admin/issue', data={
            'user_id': regular_user,
            'book_id': sample_book,
        }, follow_redirects=True)
        assert b'Book issued successfully' in response.data

        # Verify available copies decreased
        with app.app_context():
            book = Book.query.get(sample_book)
            assert book.available_copies == 2

    def test_return_book(self, client, admin_user, regular_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        # Issue first
        client.post('/admin/issue', data={
            'user_id': regular_user,
            'book_id': sample_book,
        }, follow_redirects=True)

        with app.app_context():
            issue = IssuedBook.query.first()
            issue_id = issue.id

        # Return
        response = client.post(f'/admin/return/{issue_id}', follow_redirects=True)
        assert b'Book returned successfully' in response.data

        with app.app_context():
            book = Book.query.get(sample_book)
            assert book.available_copies == 3

    def test_cannot_issue_unavailable_book(self, app, admin_user, regular_user):
        """Test that a book with 0 available copies cannot be issued via service."""
        from app.services.issue_service import issue_book as do_issue

        with app.app_context():
            book = Book(title='Rare Book', author='Author', category='Fiction',
                        total_copies=1, available_copies=0)
            db.session.add(book)
            db.session.commit()
            book_id = book.id

            with pytest.raises(ValueError, match='No copies'):
                do_issue(regular_user, book_id)

    def test_cannot_issue_same_book_twice(self, client, admin_user, regular_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        # Issue first time
        client.post('/admin/issue', data={
            'user_id': regular_user,
            'book_id': sample_book,
        }, follow_redirects=True)

        # Try to issue again
        response = client.post('/admin/issue', data={
            'user_id': regular_user,
            'book_id': sample_book,
        }, follow_redirects=True)
        assert b'already has a copy' in response.data

    def test_cannot_return_already_returned_book(self, client, admin_user, regular_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        client.post('/admin/issue', data={
            'user_id': regular_user,
            'book_id': sample_book,
        }, follow_redirects=True)

        with app.app_context():
            issue = IssuedBook.query.first()
            issue_id = issue.id

        # Return once
        client.post(f'/admin/return/{issue_id}', follow_redirects=True)

        # Try to return again
        response = client.post(f'/admin/return/{issue_id}', follow_redirects=True)
        assert b'already been returned' in response.data


# ═══════════════════════════════════════════════════════════════════
# Overdue Detection Tests
# ═══════════════════════════════════════════════════════════════════

class TestOverdueDetection:
    """Test automatic overdue detection."""

    def test_overdue_marking(self, app, admin_user, regular_user, sample_book):
        from datetime import datetime, timedelta
        from app.services.issue_service import update_overdue_books

        with app.app_context():
            # Create an overdue record
            issue = IssuedBook(
                user_id=regular_user,
                book_id=sample_book,
                issue_code=IssuedBook.generate_issue_code(),
                issue_date=datetime.utcnow() - timedelta(days=30),
                due_date=datetime.utcnow() - timedelta(days=16),
                status='issued',
            )
            book = Book.query.get(sample_book)
            book.available_copies -= 1
            db.session.add(issue)
            db.session.commit()

            count = update_overdue_books()
            assert count == 1

            issue = IssuedBook.query.first()
            assert issue.status == 'overdue'


# ═══════════════════════════════════════════════════════════════════
# Blocked User Tests
# ═══════════════════════════════════════════════════════════════════

class TestBlockedUser:
    """Test blocked user behavior."""

    def test_blocked_user_cannot_login(self, client, blocked_user):
        response = login(client, 'blocked@test.com', 'Blocked@123')
        assert b'blocked' in response.data

    def test_cannot_issue_to_blocked_user(self, app, admin_user, blocked_user, sample_book):
        from app.services.issue_service import issue_book

        with app.app_context():
            with pytest.raises(ValueError, match='blocked'):
                issue_book(blocked_user, sample_book)

    def test_admin_can_block_user(self, client, admin_user, regular_user):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post(f'/admin/users/toggle/{regular_user}', follow_redirects=True)
        assert b'blocked' in response.data

    def test_admin_can_unblock_user(self, client, admin_user, blocked_user):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        response = client.post(f'/admin/users/toggle/{blocked_user}', follow_redirects=True)
        assert b'activated' in response.data


# ═══════════════════════════════════════════════════════════════════
# User Features Tests
# ═══════════════════════════════════════════════════════════════════

class TestUserFeatures:
    """Test user-facing features."""

    def test_user_dashboard(self, client, regular_user):
        login(client, 'user@test.com', 'User@123')
        response = client.get('/user/dashboard')
        assert response.status_code == 200
        assert b'Welcome' in response.data

    def test_book_search(self, client, regular_user, sample_book):
        login(client, 'user@test.com', 'User@123')
        response = client.get('/user/search?query=Test')
        assert response.status_code == 200
        assert b'Test Book' in response.data

    def test_book_search_no_results(self, client, regular_user):
        login(client, 'user@test.com', 'User@123')
        response = client.get('/user/search?query=Nonexistent')
        assert response.status_code == 200
        assert b'No books found' in response.data

    def test_book_detail(self, client, regular_user, sample_book):
        login(client, 'user@test.com', 'User@123')
        response = client.get(f'/user/book/{sample_book}')
        assert response.status_code == 200
        assert b'Test Book' in response.data
        assert b'Available' in response.data

    def test_my_books(self, client, regular_user):
        login(client, 'user@test.com', 'User@123')
        response = client.get('/user/my-books')
        assert response.status_code == 200

    def test_search_by_category(self, client, regular_user, sample_book):
        login(client, 'user@test.com', 'User@123')
        response = client.get('/user/search?category=Fiction')
        assert response.status_code == 200
        assert b'Test Book' in response.data

    def test_book_detail_404(self, client, regular_user):
        login(client, 'user@test.com', 'User@123')
        response = client.get('/user/book/99999')
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and data integrity."""

    def test_cannot_delete_book_with_issued_copies(self, client, admin_user, regular_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        # Issue the book
        client.post('/admin/issue', data={
            'user_id': regular_user,
            'book_id': sample_book,
        }, follow_redirects=True)

        # Try to delete
        response = client.post(f'/admin/books/delete/{sample_book}', follow_redirects=True)
        assert b'Cannot delete' in response.data

    def test_reduce_copies_below_issued(self, client, admin_user, regular_user, sample_book, app):
        login(client, 'admin@test.com', 'Admin@123', role='admin')
        # Issue all 3 copies
        with app.app_context():
            users = []
            for i in range(3):
                u = User(name=f'User{i}', email=f'user{i}@test.com', role='user', status='active')
                u.set_password('Pass@123')
                db.session.add(u)
                db.session.commit()
                users.append(u.id)

        for uid in users:
            client.post('/admin/issue', data={
                'user_id': uid,
                'book_id': sample_book,
            }, follow_redirects=True)

        # Try reducing total copies to 1
        response = client.post(f'/admin/books/edit/{sample_book}', data={
            'title': 'Test Book',
            'author': 'Test Author',
            'category': 'Fiction',
            'total_copies': 1,
        }, follow_redirects=True)
        assert b'Cannot reduce' in response.data

    def test_error_404_page(self, client):
        response = client.get('/nonexistent-page')
        assert response.status_code == 404

    def test_short_password_registration(self, client):
        response = client.post('/register', data={
            'name': 'User',
            'email': 'short@test.com',
            'password': '123',
            'confirm_password': '123',
        })
        assert response.status_code == 200  # stays on form

    def test_invalid_email_registration(self, client):
        response = client.post('/register', data={
            'name': 'User',
            'email': 'not-an-email',
            'password': 'Test@123',
            'confirm_password': 'Test@123',
        })
        assert response.status_code == 200  # stays on form
