import os
import zipfile
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables for DB credentials
load_dotenv()

def create_backup():
    # 1. Configuration
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = f"backups/backup_{timestamp}"
    os.makedirs(backup_folder, exist_ok=True)
    
    db_name = os.getenv('DB_NAME', 'olms_db')
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD')
    
    print(f"--- Starting Backup: {timestamp} ---")
    
    if not db_pass:
        print("⚠️  Warning: No 'DB_PASSWORD' found in .env file. Attempting connection without password...")
    
    # 2. Database Backup (MySQL Dump)
    sql_file = os.path.join(backup_folder, f"{db_name}_dump.sql")
    print(f"Dumping database '{db_name}'...")
    
    # Path found on your system
    mysqldump_path = r"C:\Program Files\MySQL\MySQL Server 9.6\bin\mysqldump.exe"
    
    try:
        # Construct the mysqldump command
        # Use -p without space for the password if it exists
        cmd = [
            mysqldump_path,
            f'--user={db_user}',
            f'--password={db_pass}' if db_pass else '--password=',
            db_name
        ]
        with open(sql_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
        print(f"✓ Database dump created: {sql_file}")
    except Exception as e:
        print(f"✗ Database dump failed: {e}")
        print("Tip: Make sure 'mysqldump' is installed and in your system PATH.")

    # 3. Code Backup (Zip)
    zip_filename = f"olms_source_{timestamp}.zip"
    zip_path = os.path.join(backup_folder, zip_filename)
    print(f"Zipping source code to {zip_filename}...")
    
    # Files/folders to exclude
    exclude = {'.git', 'venv', '__pycache__', 'backups', '.pytest_cache', 'node_modules', '.gemini'}
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk('.'):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in exclude]
                
                for file in files:
                    if file not in exclude:
                        file_path = os.path.join(root, file)
                        # Store file with relative path
                        arcname = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arcname)
        print(f"✓ Source code zipped: {zip_path}")
    except Exception as e:
        print(f"✗ Zipping failed: {e}")

    print(f"\n--- Backup Complete! ---")
    print(f"Your backup is stored in: {os.path.abspath(backup_folder)}")
    print("Keep this folder safe (External drive or Cloud storage is recommended).")

if __name__ == "__main__":
    create_backup()
