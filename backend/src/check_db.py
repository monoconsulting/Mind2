
import sys
import os
sys.path.append(os.getcwd())
from services.db.connection import db_cursor

def check_columns():
    try:
        with db_cursor() as cur:
            cur.execute("DESCRIBE unified_files")
            columns = [row[0] for row in cur.fetchall()]
            print(f"Columns: {columns}")
            
            has_ingest = 'ingest_source_channel' in columns
            has_source = 'source_channel' in columns
            print(f"Has ingest_source_channel: {has_ingest}")
            print(f"Has source_channel: {has_source}")
            
            if has_ingest or has_source:
                col = 'ingest_source_channel' if has_ingest else 'source_channel'
                cur.execute(f"SELECT {col}, COUNT(*) FROM unified_files GROUP BY {col}")
                print("Values:")
                for row in cur.fetchall():
                    print(row)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
