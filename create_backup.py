import os
import zipfile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables (if any)
load_dotenv()

def create_backup():
    # 1. Configuration
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = f"backups/backup_{timestamp}"
    os.makedirs(backup_folder, exist_ok=True)
    
    print(f"--- Starting OLMS Backup (SQLite Mode): {timestamp} ---")

    # 2. Code & Database Backup (Zip)
    zip_filename = f"olms_full_backup_{timestamp}.zip"
    zip_path = os.path.join(backup_folder, zip_filename)
    
    # Files/folders to exclude from the zip to keep it small
    exclude = {'.git', 'venv', '__pycache__', 'backups', '.pytest_cache', 'node_modules', '.gemini'}
    
    print(f"Bundling your Code and Database (olms.db) into {zip_filename}...")
    
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
        
        print(f"✓ FULL BACKUP CREATED: {zip_path}")
        print(f"✓ Included: All source code, styles, and the library database (olms.db)")
    except Exception as e:
        print(f"✗ Backup failed: {e}")

    print(f"\n--- Backup Complete! ---")
    print(f"Your full system backup is stored in: {os.path.abspath(backup_folder)}")
    print("Keep this .zip file safe (on a USB or Cloud) and you can restore your library anywhere!")

if __name__ == "__main__":
    create_backup()
