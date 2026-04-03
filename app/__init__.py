import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
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

    # Health Check for Render
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "database": "connected"}, 200

    # Serve Service Worker at root level for Web Push scope
    @app.route('/sw.js')
    def sw():
        return app.send_static_file('sw.js')

    # Create database tables if they don't exist (needed for Render/production)
    with app.app_context():
        app.logger.info(f'Database URI: {app.config["SQLALCHEMY_DATABASE_URI"][:30]}...')
        db.create_all()
        _create_default_admin()
        
        # Optimized Super-Check for PostgreSQL Schema (Render Speed Fix)
        from sqlalchemy import text
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url.startswith('postgres'):
            import psycopg2
            try:
                conn = psycopg2.connect(db_url.replace('postgresql://', 'postgres://'))
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Check for all missing columns in one go (Super-Check)
                cursor.execute("""
                    SELECT table_name, column_name 
                    FROM information_schema.columns 
                    WHERE table_name IN ('issued_books', 'users', 'books');
                """)
                existing_cols = cursor.fetchall()
                col_map = {(t, c) for t, c in existing_cols}
                
                # List of needed columns: (table, col, sql_type)
                needed = [
                    ('issued_books', 'fine_amount', 'FLOAT NOT NULL DEFAULT 0.0'),
                    ('issued_books', 'fine_paid', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('issued_books', 'notified_due_soon', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('users', 'last_active_at', 'TIMESTAMP NULL'),
                    ('books', 'image_url', 'TEXT NULL'),
                    ('books', 'image_public_id', 'VARCHAR(255) NULL')
                ]
                
                for table, col, sql_type in needed:
                    if (table, col) not in col_map:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type};")
                        app.logger.info(f"Fixed missing column: {table}.{col}")
                
                conn.close()
            except Exception as e:
                app.logger.error(f"Postgres Speed-Migration Error: {e}")
        else:
            # Fallback for local SQLite/MySQL
            for table, col, sql_type in [
                ('issued_books', 'fine_amount', 'FLOAT NOT NULL DEFAULT 0.0'),
                ('issued_books', 'fine_paid', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                ('issued_books', 'notified_due_soon', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                ('users', 'last_active_at', 'DATETIME NULL'),
                ('books', 'image_url', 'TEXT NULL'),
                ('books', 'image_public_id', 'VARCHAR(255) NULL')
            ]:
                try:
                    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type}"))
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
