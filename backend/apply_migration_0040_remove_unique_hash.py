import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.db.connection import db_cursor

def run_migration():
    print("Removing unique constraint on content_hash...")
    try:
        with db_cursor() as cur:
            # Check for index name. Usually it's content_hash or idx_content_hash
            cur.execute("SHOW INDEX FROM unified_files WHERE Key_name='content_hash' OR Key_name='idx_content_hash'")
            rows = cur.fetchall()
            for row in rows:
                key_name = row[2]
                non_unique = row[1]
                if non_unique == 0: # It is unique
                    print(f"Dropping unique index {key_name}")
                    cur.execute(f"DROP INDEX {key_name} ON unified_files")
                    print(f"Adding non-unique index {key_name}")
                    cur.execute(f"CREATE INDEX {key_name} ON unified_files (content_hash)")
                else:
                    print(f"Index {key_name} is already non-unique.")
            
            if not rows:
                print("No index found on content_hash. Creating non-unique index.")
                cur.execute("CREATE INDEX idx_content_hash ON unified_files (content_hash)")

            print("Migration applied successfully.")
    except Exception as e:
        print(f"Error applying migration: {e}")

if __name__ == "__main__":
    run_migration()
