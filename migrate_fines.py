import sqlite3
import os

def run_migration():
    db_path = os.path.join(os.path.dirname(__file__), 'olms.db')
    print(f"Connecting to the SQLite database at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        print("Please make sure you are in the correct directory or the database has been initialized.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Checking for existing columns in 'issued_books'...")
        # Get existing columns
        cursor.execute("PRAGMA table_info(issued_books)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add fine_amount if it doesn't exist
        if 'fine_amount' not in columns:
            print("Adding 'fine_amount' column...")
            cursor.execute("ALTER TABLE issued_books ADD COLUMN fine_amount FLOAT NOT NULL DEFAULT 0.0")
        else:
            print("'fine_amount' column already exists.")

        # Add fine_paid if it doesn't exist
        if 'fine_paid' not in columns:
            print("Adding 'fine_paid' column...")
            cursor.execute("ALTER TABLE issued_books ADD COLUMN fine_paid BOOLEAN NOT NULL DEFAULT 0")
        else:
            print("'fine_paid' column already exists.")
            
        conn.commit()
        print("\n✅ Migration successful! Both fields are live in your local olms.db database.")
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
