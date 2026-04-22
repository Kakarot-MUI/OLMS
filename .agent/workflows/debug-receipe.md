---
description: Step-by-step recipe for debugging the OLMS Flask application
---

# Debug Recipe for OLMS (Online Library Management System)

Use this workflow when the application crashes, shows unexpected behavior, or tests fail.

---

## 1. Activate the Virtual Environment

```powershell
# From the project root (d:\olms)
d:\olms\New folder\venv\Scripts\Activate.ps1
```

---

## 2. Reproduce the Issue

Start the development server and observe the error:

// turbo
```powershell
cd d:\olms && python run.py
```

- Open `http://localhost:5000` in a browser.
- Navigate to the page or perform the action that triggers the bug.
- Read the traceback in the terminal and note the **file**, **line number**, and **exception type**.

---

## 3. Run the Test Suite

Run all existing tests to see which pass and which fail:

```powershell
cd d:\olms && python -m pytest "New folder/tests/test_app.py" -v --tb=short
```

- Note every **FAILED** test name and its short traceback.
- If a specific test matches the bug, run it in isolation with extra detail:

```powershell
python -m pytest "New folder/tests/test_app.py::TestClassName::test_method_name" -v --tb=long
```

---

## 4. Check Recent Changes

Review recent git changes to identify what might have introduced the bug:

```powershell
cd d:\olms && git log --oneline -10
```

```powershell
cd d:\olms && git diff HEAD~1 --stat
```

If the issue was introduced recently, inspect the full diff of the relevant files:

```powershell
cd d:\olms && git diff HEAD~1 -- <file_path>
```

---

## 5. Inspect Key Files

Depending on the error type, inspect the relevant source files:

| Error Area              | Files to Check                                                         |
|-------------------------|------------------------------------------------------------------------|
| **App startup / config**| `config.py`, `app/__init__.py`, `.env`                                 |
| **Authentication**      | `app/routes/auth.py`, `app/forms.py`, `app/decorators.py`             |
| **Admin routes**        | `app/routes/admin.py`                                                  |
| **User routes**         | `app/routes/user.py`                                                   |
| **Models / DB**         | `app/models.py`, `migrations/`                                         |
| **Book issue/return**   | `app/services/issue_service.py`, `app/services/book_service.py`       |
| **Templates**           | `app/templates/` (check the template named in the Jinja2 traceback)   |
| **Static / CSS / JS**   | `app/static/`                                                          |

---

## 6. Use Flask Shell for Interactive Debugging

Launch the Flask shell to query the database and inspect model state:

```powershell
cd d:\olms && $env:FLASK_APP="run.py"; $env:FLASK_ENV="development"; python -m flask shell
```

Useful shell commands:

```python
from app.models import User, Book, IssuedBook
from app import db

# Check all users
User.query.all()

# Check all books
Book.query.all()

# Check issued books and their status
IssuedBook.query.filter_by(status='issued').all()

# Check for overdue books
from datetime import datetime
IssuedBook.query.filter(IssuedBook.due_date < datetime.utcnow(), IssuedBook.status == 'issued').all()
```

---

## 7. Enable Verbose Logging

If the error is not obvious, add temporary logging to the suspected route or service:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add inside the function you are debugging:
logger.debug(f"Variable state: {variable_name}")
```

Or use Flask's built-in logger:

```python
from flask import current_app
current_app.logger.debug(f"Debugging info: {value}")
```

---

## 8. Database Debugging

If the issue is database-related:

```powershell
# Check migration status
cd d:\olms && python -m flask db current

# Check migration history
cd d:\olms && python -m flask db history

# If schema is out of sync, create and apply a new migration
cd d:\olms && python -m flask db migrate -m "describe change"
cd d:\olms && python -m flask db upgrade
```

To reset the dev database entirely (SQLite):

```powershell
# Delete the SQLite database file and re-create
Remove-Item d:\olms\olms.db
cd d:\olms && python -m flask db upgrade
```

---

## 9. Common Issues & Quick Fixes

| Symptom                                 | Likely Cause                              | Fix                                                        |
|-----------------------------------------|-------------------------------------------|------------------------------------------------------------|
| `ImportError` on startup                | Circular import or missing package        | Check `requirements.txt`, run `pip install -r requirements.txt` |
| `OperationalError: no such table`       | DB not migrated                           | Run `flask db upgrade`                                      |
| `TemplateNotFound`                      | Wrong template path in `render_template`  | Verify file exists in `app/templates/`                      |
| `405 Method Not Allowed`               | Route missing `methods=['POST']`          | Add POST to the route `@bp.route(..., methods=[...])`       |
| `CSRF token missing`                   | Form missing `{{ form.hidden_tag() }}`    | Add hidden tag to the HTML form                             |
| Login redirects to index               | `@login_required` on route               | Ensure user is logged in and `login_manager.login_view` is set |
| `IntegrityError` / unique constraint   | Duplicate data or missing validation      | Check unique columns in `models.py`                         |
| Admin can't access admin pages         | Role check failing in `decorators.py`     | Verify `current_user.role == 'admin'`                       |
| Tests fail with `401` / `403`          | Auth not set up in test                   | Use the `login()` helper before hitting protected routes    |

---

## 10. Validate the Fix

After applying a fix, verify it works end-to-end:

// turbo
```powershell
cd d:\olms && python -m pytest "New folder/tests/test_app.py" -v --tb=short
```

Then manually test in the browser:

// turbo
```powershell
cd d:\olms && python run.py
```

- Confirm the original bug is resolved.
- Confirm no other pages or features broke.
- Commit the fix:

```powershell
cd d:\olms && git add -A && git commit -m "fix: describe what was fixed"
```
