# Online Library Management System (OLMS)

A production-ready library management system built with Flask, MySQL, and Bootstrap 5. Supports Admin (Librarian) and User (Member) roles with book management, issue/return tracking, and reporting.

## Features

### Admin (Librarian)
- Dashboard with statistics (books, members, issued, overdue)
- Book CRUD (add, edit, delete) with copy management
- Member management (view, block/unblock)
- Issue books to members with automatic due date
- Process book returns
- View issued/overdue books with filtering
- Reports page with full analytics

### User (Member)
- Self-registration and login
- Browse and search books by title, author, or category
- View book details and availability
- View personal borrowing history
- Dashboard with active and returned books

### Security
- bcrypt password hashing
- CSRF protection on all forms
- Role-based access control (admin routes protected)
- SQL injection prevention via ORM
- Input validation on all forms
- Blocked user enforcement

---

## Technology Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3, Flask, SQLAlchemy ORM     |
| Database   | MySQL (PyMySQL driver)              |
| Frontend   | HTML5, CSS3, Bootstrap 5, Jinja2    |
| Auth       | Flask-Login, Flask-Bcrypt           |
| Forms      | Flask-WTF, WTForms                  |
| Migrations | Flask-Migrate (Alembic)             |
| Deployment | Gunicorn                            |

---

## Project Structure

```
olms/
├── run.py                  # Application entry point
├── config.py               # Configuration classes
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md               # This file
├── migrations/             # Database migrations (auto-generated)
├── tests/
│   ├── __init__.py
│   └── test_app.py         # Comprehensive test suite (35+ tests)
└── app/
    ├── __init__.py          # App factory, extension init
    ├── models.py            # User, Book, IssuedBook models
    ├── forms.py             # WTF forms with validation
    ├── decorators.py        # admin_required, active_required
    ├── routes/
    │   ├── __init__.py
    │   ├── auth.py          # Login, register, logout
    │   ├── admin.py         # Admin dashboard, CRUD, issue/return
    │   ├── user.py          # User dashboard, search, book detail
    │   └── errors.py        # 403, 404, 500 handlers
    ├── services/
    │   ├── __init__.py
    │   ├── book_service.py  # Book CRUD, search, pagination
    │   └── issue_service.py # Issue/return, overdue, stats
    ├── templates/
    │   ├── base.html
    │   ├── auth/            # login.html, register.html
    │   ├── admin/           # layout, dashboard, books, users, etc.
    │   ├── user/            # layout, dashboard, search, etc.
    │   └── errors/          # 403.html, 404.html, 500.html
    └── static/
        ├── css/style.css    # Custom design system
        └── js/main.js       # Client-side utilities
```

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- MySQL 5.7+ or MariaDB
- pip

### 1. Clone and Install Dependencies

```bash
cd olms
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` with your MySQL credentials and set your initial Admin account:
```
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=olms_db

# Initial Admin Setup (First run only)
ADMIN_EMAIL=admin@yourlibrary.com
ADMIN_PASSWORD=CreateAStrongPasswordHere
```

### 3. Create the Database

```sql
CREATE DATABASE olms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Run Database Migrations

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Run the Application

```bash
python run.py
```

Visit `http://localhost:5000` in your browser.

### Admin Access
Once the application is running and the database is initialized, log in using the `ADMIN_EMAIL` and `ADMIN_PASSWORD` you configured in the `.env` file. Ensure you change your password immediately from the Profile page.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests cover:
- Authentication (login, register, logout, invalid inputs)
- Access control (admin-only routes, unauthenticated access)
- Book CRUD (add, edit, delete, validation)
- Issue/return logic (availability, duplicates, return flow)
- Overdue detection
- Blocked user enforcement
- Edge cases (data integrity, copy count limits, error pages)

---

## Deployment with Gunicorn (Production)

### 1. Set Production Environment

```bash
export FLASK_ENV=production
export SECRET_KEY=your-production-secret-key
```

### 2. Run with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

### 3. Recommended Setup

- Use **Nginx** as a reverse proxy in front of Gunicorn
- Use **systemd** service for process management
- Enable **SSL/TLS** via Let's Encrypt
- Set up **database backups**

### Sample Nginx Config

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Database Schema

### Users Table
| Column        | Type         | Constraints          |
|---------------|--------------|----------------------|
| id            | Integer      | Primary Key          |
| name          | String(120)  | Not Null             |
| email         | String(120)  | Unique, Not Null     |
| password_hash | String(256)  | Not Null             |
| role          | String(20)   | Default: 'user'      |
| status        | String(20)   | Default: 'active'    |
| created_at    | DateTime     | Default: UTC now     |

### Books Table
| Column          | Type         | Constraints                     |
|-----------------|--------------|----------------------------------|
| id              | Integer      | Primary Key                     |
| title           | String(255)  | Not Null                        |
| author          | String(255)  | Not Null                        |
| category        | String(100)  | Not Null                        |
| total_copies    | Integer      | Not Null, >= 0                  |
| available_copies| Integer      | Not Null, >= 0, <= total_copies |
| created_at      | DateTime     | Default: UTC now                |

### Issued Books Table
| Column      | Type      | Constraints                     |
|-------------|-----------|---------------------------------|
| id          | Integer   | Primary Key                     |
| user_id     | Integer   | FK → users.id                   |
| book_id     | Integer   | FK → books.id                   |
| issue_date  | DateTime  | Not Null                        |
| due_date    | DateTime  | Not Null                        |
| return_date | DateTime  | Nullable                        |
| status      | String(20)| Default: 'issued'               |

---

## Testing Checklist

- [x] Login with valid credentials succeeds
- [x] Login with invalid credentials shows error
- [x] Blocked user cannot login
- [x] Registration with duplicate email fails
- [x] Password mismatch registration fails
- [x] Admin routes return 403 for regular users
- [x] Unauthenticated users redirected to login
- [x] Book CRUD operations work correctly
- [x] Issue book decreases available copies
- [x] Return book increases available copies
- [x] Cannot issue unavailable book
- [x] Cannot issue same book twice to same user
- [x] Cannot return already returned book
- [x] Cannot delete book with issued copies
- [x] Cannot reduce copies below issued count
- [x] Overdue books automatically detected
- [x] Cannot issue to blocked user
- [x] Admin can block/unblock users
- [x] Search by title/author works
- [x] Search by category works
- [x] 404 page displays correctly
- [x] Short password rejected
- [x] Invalid email rejected
