import os
import psycopg2
from dotenv import load_dotenv

# Load from .env if running from local pushing to remote
load_dotenv('.env')

# Default to the platform's injected DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# If no DATABASE_URL, fallback to config
if not DATABASE_URL:
    try:
        from config import ProductionConfig
        DATABASE_URL = ProductionConfig._db_url
    except ImportError:
        pass

def run_migration():
    if not DATABASE_URL:
        print("❌ Error: No DATABASE_URL found. Please set DATABASE_URL environment variable.")
        return

    print("🚀 Connecting to PostgreSQL Database for Master Synchronization...")
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        # 1. BOOKS TABLE
        print("\n--- Synchronizing BOOKS table ---")
        columns = [
            ("access_number", "VARCHAR(50) DEFAULT NULL"),
            ("publication", "VARCHAR(255) NOT NULL DEFAULT 'Unknown'"),
            ("image_url", "VARCHAR(500) DEFAULT NULL"),
            ("image_public_id", "VARCHAR(255) DEFAULT NULL")
        ]
        for col_name, col_type in columns:
            try:
                cursor.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_type};")
                print(f"✅ Added '{col_name}' column.")
            except psycopg2.errors.DuplicateColumn:
                print(f"ℹ️ '{col_name}' column already exists.")

        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_books_access_number ON books (access_number);")
            print("✅ Created index on 'access_number'.")
        except Exception as e:
            print(f"ℹ️ Could not create index: {e}")

        # 2. USERS TABLE
        print("\n--- Synchronizing USERS table ---")
        columns = [
            ("last_active_at", "TIMESTAMP DEFAULT NULL"),
            ("roll_number", "VARCHAR(50) DEFAULT NULL"),
            ("phone", "VARCHAR(20) DEFAULT NULL"),
            ("division", "VARCHAR(20) DEFAULT NULL"),
            ("department", "VARCHAR(100) DEFAULT NULL"),
            ("semester", "INTEGER DEFAULT NULL")
        ]
        for col_name, col_type in columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")
                print(f"✅ Added '{col_name}' column.")
            except psycopg2.errors.DuplicateColumn:
                print(f"ℹ️ '{col_name}' column already exists.")

        # 3. ISSUED_BOOKS TABLE
        print("\n--- Synchronizing ISSUED_BOOKS table ---")
        columns = [
            ("fine_amount", "FLOAT NOT NULL DEFAULT 0.0"),
            ("fine_paid", "BOOLEAN NOT NULL DEFAULT FALSE")
        ]
        for col_name, col_type in columns:
            try:
                cursor.execute(f"ALTER TABLE issued_books ADD COLUMN {col_name} {col_type};")
                print(f"✅ Added '{col_name}' column.")
            except psycopg2.errors.DuplicateColumn:
                print(f"ℹ️ '{col_name}' column already exists.")

        print("\n🎉 Master Synchronization Complete! Production database is now fully updated.")

    except psycopg2.Error as e:
        print(f"\n❌ PostgreSQL Migration Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    run_migration()
