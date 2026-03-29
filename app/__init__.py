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

    # Activity Tracking (Online status)
    @app.before_request
    def update_last_active():
        from flask_login import current_user
        from datetime import datetime
        if current_user.is_authenticated:
            current_user.last_active_at = datetime.utcnow()
            db.session.commit()

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
                
        from app.models import User
        admin_is_online = False
        if current_user.is_authenticated and current_user.role == 'user':
            admin = User.query.filter_by(role='admin').first()
            if admin:
                admin_is_online = admin.is_online
                
        return dict(
            unread_chat_count=unread_chat_count,
            due_books_count=due_books_count,
            admin_is_online=admin_is_online
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
        
        # Auto-migrate new columns for existing production databases (PostgreSQL/MySQL/SQLite compat)
        import os
        from sqlalchemy import text
        
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url.startswith('postgres'):
            import psycopg2
            # Connect directly to perform robust PostgreSQL schema alterations
            # psycopg2 is required for Render deployments to avoid transaction block errors on duplicate columns
            try:
                # Need to use the raw postgres:// URL for psycopg2 if that's what's in the env
                conn = psycopg2.connect(db_url.replace('postgresql://', 'postgres://'))
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Check if fine_amount exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='issued_books' AND column_name='fine_amount';
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE issued_books ADD COLUMN fine_amount FLOAT NOT NULL DEFAULT 0.0;")
                    app.logger.info("Added fine_amount column to PostgreSQL.")

                # Check if fine_paid exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='issued_books' AND column_name='fine_paid';
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE issued_books ADD COLUMN fine_paid BOOLEAN NOT NULL DEFAULT FALSE;")
                    app.logger.info("Added fine_paid column to PostgreSQL.")
                    
                # Check if notified_due_soon exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='issued_books' AND column_name='notified_due_soon';
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE issued_books ADD COLUMN notified_due_soon BOOLEAN NOT NULL DEFAULT FALSE;")
                    app.logger.info("Added notified_due_soon column to PostgreSQL.")
                
                # Check if last_active_at exists in users table
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='last_active_at';
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP NULL;")
                    app.logger.info("Added last_active_at column to PostgreSQL.")
                    
                conn.close()
            except Exception as e:
                app.logger.error(f"PostgreSQL Auto-Migration Error: {e}")
        else:
            # Fallback for local SQLite/MySQL
            try:
                db.session.execute(text("ALTER TABLE issued_books ADD COLUMN fine_amount FLOAT NOT NULL DEFAULT 0.0"))
                db.session.commit()
            except Exception:
                db.session.rollback()

            try:
                db.session.execute(text("ALTER TABLE issued_books ADD COLUMN fine_paid BOOLEAN NOT NULL DEFAULT FALSE"))
                db.session.commit()
            except Exception:
                db.session.rollback()
                
            try:
                db.session.execute(text("ALTER TABLE issued_books ADD COLUMN notified_due_soon BOOLEAN NOT NULL DEFAULT FALSE"))
                db.session.commit()
            except Exception:
                db.session.rollback()

            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN last_active_at DATETIME NULL"))
                db.session.commit()
            except Exception:
                db.session.rollback()

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
