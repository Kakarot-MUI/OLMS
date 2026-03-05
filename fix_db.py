import sqlite3
import os

db_path = r'D:\olms\olms.db'

def fix():
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # List tables before
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables before cleanup: {tables}")

    # Drop conflicting tables
    for table in ['saved_books', 'reviews']:
        if table in tables:
            print(f"Dropping table {table}...")
            cursor.execute(f"DROP TABLE {table};")
    
    conn.commit()

    # List tables after
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables_after = [t[0] for t in cursor.fetchall()]
    print(f"Tables after cleanup: {tables_after}")
    
    conn.close()
    print("Cleanup complete. Please try 'flask db upgrade' now.")

if __name__ == "__main__":
    fix()
