import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.db.connection import db_cursor

def run_migration():
    sql = """
    ALTER TABLE unified_files ADD COLUMN is_duplicate BOOLEAN DEFAULT FALSE;
    ALTER TABLE unified_files ADD INDEX idx_is_duplicate (is_duplicate);
    """
    
    print("Applying migration...")
    try:
        with db_cursor() as cur:
            # Check if column exists first to avoid error
            cur.execute("SHOW COLUMNS FROM unified_files LIKE 'is_duplicate'")
            if cur.fetchone():
                print("Column is_duplicate already exists. Skipping.")
            else:
                # Split statements
                statements = [s.strip() for s in sql.split(';') if s.strip()]
                for stmt in statements:
                    print(f"Executing: {stmt}")
                    cur.execute(stmt)
                print("Migration applied successfully.")
    except Exception as e:
        print(f"Error applying migration: {e}")

if __name__ == "__main__":
    run_migration()
