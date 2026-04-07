import os
import psycopg2
from dotenv import load_dotenv

# Load from .env if running from local pushing to remote
load_dotenv('.env')

# Import exact fallback DB logic from config
from config import ProductionConfig
DATABASE_URL = ProductionConfig._db_url

def run_migration():
    if not DATABASE_URL:
        print("Error: No DATABASE_URL found.")
        return

    print(f"Connecting to PostgreSQL Database to add Access Number field...")
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Adding 'access_number' column to books table...")
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN access_number VARCHAR(50) DEFAULT NULL;")
            print("Successfully added 'access_number' column.")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_books_access_number ON books (access_number);")
            print("Successfully created index on 'access_number'.")
        except psycopg2.errors.DuplicateColumn:
            print("'access_number' column already exists.")

        print("\nMigration Complete! Your Render database is successfully upgraded.")

    except psycopg2.Error as e:
        print(f"\nPostgreSQL Migration Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    run_migration()
