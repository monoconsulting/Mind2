import uuid
import time
from services.db.connection import db_cursor

def seed_data():
    orphan_id = str(uuid.uuid4())
    stalled_id = str(uuid.uuid4())
    
    print(f"Seeding Orphan File: {orphan_id}")
    print(f"Seeding Stalled File: {stalled_id}")

    with db_cursor() as cur:
        # 1. Create Orphan File (Processing, no workflow run)
        cur.execute(
            """
            INSERT INTO unified_files (
                id, file_type, workflow_type, ocr_raw, other_data, content_hash,
                submitted_by, original_filename, ai_status,
                mime_type, file_suffix, original_file_id,
                original_file_name, original_file_size, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW() - INTERVAL 10 MINUTE)
            """,
            (
                orphan_id, "receipt", "WF1_RECEIPT", "", "{}", f"hash_{orphan_id}",
                "tester", "test_orphan_browser.jpg", "processing",
                "image/jpeg", ".jpg", orphan_id, "test_orphan_browser.jpg", 1024
            ),
        )

        # 2. Create Stalled File with Workflow Run
        cur.execute(
            """
            INSERT INTO unified_files (
                id, file_type, workflow_type, ocr_raw, other_data, content_hash,
                submitted_by, original_filename, ai_status,
                mime_type, file_suffix, original_file_id,
                original_file_name, original_file_size, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW() - INTERVAL 10 MINUTE)
            """,
            (
                stalled_id, "receipt", "WF1_RECEIPT", "", "{}", f"hash_{stalled_id}",
                "tester", "test_stalled_browser.jpg", "processing",
                "image/jpeg", ".jpg", stalled_id, "test_stalled_browser.jpg", 1024
            ),
        )
        
        # Create a stalled workflow run
        cur.execute(
            """
            INSERT INTO workflow_runs (
                workflow_key, source_channel, file_id, content_hash,
                status, current_stage, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW() - INTERVAL 10 MINUTE)
            """,
            ("WF1_RECEIPT", "manual_upload", stalled_id, f"hash_{stalled_id}", "running", "ai_pipeline")
        )
        
    print("Seeding complete.")

if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"Error: {e}")
