from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from config import config_by_name

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
bcrypt = Bcrypt()
csrf = CSRFProtect()

login_manager.login_view = 'auth.index'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app(config_name='development'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # VAPID Keys for Web Push Notifications
    import os
    app.config['VAPID_PUBLIC_KEY'] = os.environ.get('VAPID_PUBLIC_KEY')
    app.config['VAPID_PRIVATE_KEY'] = os.environ.get('VAPID_PRIVATE_KEY')
    app.config['VAPID_CLAIMS'] = {
        "sub": "mailto:admin@smartlibrary.com"
    }

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)

    # Import models so they are registered
    from app import models  # noqa: F401

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.user import user_bp
    from app.routes.errors import errors_bp
    from app.routes.push import bp as push_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(errors_bp)
    app.register_blueprint(push_bp)

    # Global variables for templates (Notifications)
    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        from datetime import datetime, timedelta
        from app.models import Message, IssuedBook
        
        unread_chat_count = 0
        due_books_count = 0
        
        if current_user.is_authenticated:
            # Unread messages sent to the current user
            unread_chat_count = Message.query.filter_by(
                receiver_id=current_user.id, 
                is_read=False
            ).count()
            
            # For students: count books that are due in exactly or less than 3 days, or overdue
            if current_user.role == 'user':
                warning_date = datetime.utcnow() + timedelta(days=3)
                due_books_count = IssuedBook.query.filter(
                    IssuedBook.user_id == current_user.id,
                    IssuedBook.status == 'issued',
                    IssuedBook.due_date <= warning_date
                ).count()
                
        return dict(
            unread_chat_count=unread_chat_count,
            due_books_count=due_books_count
        )

    # Serve Service Worker at root level for Web Push scope
    @app.route('/sw.js')
    def sw():
        return app.send_static_file('sw.js')

    # Create database tables if they don't exist (needed for Render/production)
    with app.app_context():
        app.logger.info(f'Database URI: {app.config["SQLALCHEMY_DATABASE_URI"][:30]}...')
        db.create_all()
        _create_default_admin()

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
