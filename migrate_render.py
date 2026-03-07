import os
import psycopg2
from dotenv import load_dotenv

# Load from .env if running from local pushing to remote
load_dotenv('.env')

# Default to the platform's injected DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL', '')

def run_migration():
    if not DATABASE_URL:
        print("❌ Error: No DATABASE_URL found in environment variables.")
        print("Ensure you export DATABASE_URL='postgres://...' before running this script.")
        return

    print(f"Connecting to PostgreSQL Database...")
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Adding 'fine_amount' column to structured issued_books table...")
        try:
            cursor.execute("ALTER TABLE issued_books ADD COLUMN fine_amount FLOAT NOT NULL DEFAULT 0.0;")
            print("✅ 'fine_amount' successfully added.")
        except psycopg2.errors.DuplicateColumn:
            print("ℹ️ 'fine_amount' column already exists.")
            
        print("Adding 'fine_paid' column to structured issued_books table...")
        try:
            cursor.execute("ALTER TABLE issued_books ADD COLUMN fine_paid BOOLEAN NOT NULL DEFAULT FALSE;")
            print("✅ 'fine_paid' successfully added.")
        except psycopg2.errors.DuplicateColumn:
            print("ℹ️ 'fine_paid' column already exists.")

        print("\n🚀 Migration Complete! Your Render database is successfully upgraded.")
        
    except psycopg2.Error as e:
        print(f"\n❌ PostgreSQL Migration Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    run_migration()
