import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    BOOKS_PER_PAGE = int(os.environ.get('BOOKS_PER_PAGE', 12))
    ISSUE_DURATION_DAYS = int(os.environ.get('ISSUE_DURATION_DAYS', 14))

    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'olms_db')

    # Use Neon PostgreSQL by default if no DATABASE_URL is set in environment
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'olms.db')}"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dlew4kxm7')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '315187185855881')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', 'ROVV6S1fEiJ0midZKLZbbf6c_pQ')

    _db_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://neondb_owner:npg_RKQVm9tuzlP1@ep-autumn-flower-amtm02j8.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require'
    )
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = _db_url


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
