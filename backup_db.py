import os
import pyodbc
from datetime import datetime

# ==========================================
# DATABASE BACKUP CONFIGURATION
# ==========================================
DB_NAME = 'travel_cambodia_db'

# Update this if your local SQL Server has a specific instance name (e.g., r'.\SQLEXPRESS')
SERVER_NAME = r'BABABUII\SQLEXPRESS' 

# Create an absolute path for the backups folder. 
# SQL Server requires an absolute path to write the file to your hard drive.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Generate a timestamp (e.g., 20260506_160712)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_filename = f"{DB_NAME}_{timestamp}.bak"
backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

# ==========================================
# EXECUTE BACKUP
# ==========================================
def run_backup():
    print(f"⏳ Starting backup for database: {DB_NAME}...")
    
    # We connect to the 'master' database to run server-level commands
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        f"Server={SERVER_NAME};"
        "Database=master;"
        "Trusted_Connection=yes;"
    )

    try:
        # autocommit=True is REQUIRED! SQL Server does not allow BACKUP commands 
        # to run inside a standard transaction block.
        conn = pyodbc.connect(connection_string, autocommit=True)
        cursor = conn.cursor()

        # The raw T-SQL command to backup the database
        backup_query = f"BACKUP DATABASE [{DB_NAME}] TO DISK = N'{backup_filepath}' WITH INIT"
        
        cursor.execute(backup_query)
        print(f"✅ SUCCESS! Database backed up safely to:")
        print(f"📁 {backup_filepath}")

    except pyodbc.Error as e:
        print("❌ DATABASE BACKUP FAILED!")
        print("Error details:", e)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_backup()