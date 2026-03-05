import sqlite3
import os

db_path = r'D:\olms\olms.db'
revision_id = '431c3ce73e74'

def force_sync():
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop tables to be safe
    print("Dropping potentially conflicting tables...")
    cursor.execute("DROP TABLE IF EXISTS saved_books;")
    cursor.execute("DROP TABLE IF EXISTS reviews;")
    
    # Create them manually to ensure they exist exactly as needed
    print("Creating tables manually...")
    
    cursor.execute("""
    CREATE TABLE saved_books (
        id INTEGER NOT NULL, 
        user_id INTEGER NOT NULL, 
        book_id INTEGER NOT NULL, 
        saved_at DATETIME NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(book_id) REFERENCES books (id), 
        FOREIGN KEY(user_id) REFERENCES users (id), 
        UNIQUE (user_id, book_id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE reviews (
        id INTEGER NOT NULL, 
        user_id INTEGER NOT NULL, 
        book_id INTEGER NOT NULL, 
        rating INTEGER NOT NULL, 
        content TEXT, 
        created_at DATETIME NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(book_id) REFERENCES books (id), 
        FOREIGN KEY(user_id) REFERENCES users (id), 
        UNIQUE (user_id, book_id)
    );
    """)

    # Update alembic_version so Flask thinks the migration is done
    print(f"Stamping database with version {revision_id}...")
    cursor.execute("DELETE FROM alembic_version;")
    cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?);", (revision_id,))
    
    conn.commit()
    conn.close()
    print("\nSUCCESS! Database is now manually synchronized.")
    print("You don't need to run 'flask db upgrade' anymore.")

if __name__ == "__main__":
    force_sync()
