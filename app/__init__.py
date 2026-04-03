import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from config import config
from sqlalchemy import text

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
bcrypt = Bcrypt()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register Blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.routes.user import user_bp
    app.register_blueprint(user_bp)

    from app.routes.errors import errors_bp
    app.register_blueprint(errors_bp)

    # Health Check for Render
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "database": "connected"}, 200

    # Serve Service Worker at root level for Web Push scope
    @app.route('/sw.js')
    def sw():
        return app.send_static_file('sw.js')

    # Global Context Processor
    @app.context_processor
    def inject_global_counts():
        from flask_login import current_user
        from app.models import Message, IssuedBook
        from datetime import datetime
        if current_user.is_authenticated:
            unread_chat_count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
            due_books_count = 0
            if current_user.role == 'student':
                due_books_count = IssuedBook.query.filter_by(
                    user_id=current_user.id, status='issued'
                ).filter(IssuedBook.due_date < datetime.utcnow()).count()
            return dict(unread_chat_count=unread_chat_count, due_books_count=due_books_count)
        return dict(unread_chat_count=0, due_books_count=0)

    # Create database tables and handle migrations (Original Style)
    with app.app_context():
        db.create_all()
        _create_default_admin()
        
        # Simple Migrations (Original Style)
        needed_cols = [
            ('issued_books', 'fine_amount', 'FLOAT NOT NULL DEFAULT 0.0'),
            ('issued_books', 'fine_paid', 'BOOLEAN NOT NULL DEFAULT FALSE'),
            ('issued_books', 'notified_due_soon', 'BOOLEAN NOT NULL DEFAULT FALSE'),
            ('users', 'last_active_at', 'DATETIME NULL'),
            ('books', 'image_url', 'TEXT NULL'),
            ('books', 'image_public_id', 'VARCHAR(255) NULL')
        ]
        
        for table, col, sql_type in needed_cols:
            try:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type}"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        
        # Session Cleanup to ensure Render requests start fresh
        db.session.remove()

    return app

def _create_default_admin():
    """Create a default admin user if none exists."""
    from app.models import User
    try:
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                name='Administrator',
                email='admin@olms.com',
                role='admin',
                status='active',
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()
    except Exception:
        db.session.rollback()
