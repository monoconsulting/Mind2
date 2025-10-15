#!/usr/bin/env python3
"""
Script to reprocess FirstCard credit card invoice files.
This triggers OCR processing for the parent PDF which will cascade to pages.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.db.connection import db_cursor
from services.tasks import process_ocr

def get_fc_parent_files():
    """Get FC parent PDF files that need reprocessing."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, original_filename, file_type
            FROM unified_files
            WHERE submitted_by = 'invoice_upload'
              AND original_filename LIKE 'FC_%'
              AND file_type = 'cc_pdf'
            ORDER BY created_at
        """)
        return cur.fetchall()

def main():
    print("Finding FC files to reprocess...")
    files = get_fc_parent_files()

    if not files:
        print("No FC parent files found.")
        return

    print(f"Found {len(files)} FC parent file(s) to reprocess:")
    for file_id, filename, file_type in files:
        print(f"  - {filename} ({file_id}, type: {file_type})")

    print("\nTriggering reprocessing...")
    for file_id, filename, file_type in files:
        print(f"Processing {filename} ({file_id})...")
        try:
            # Trigger OCR processing which will route to correct pipeline
            if hasattr(process_ocr, 'delay'):
                # Celery async mode
                result = process_ocr.delay(file_id)
                print(f"  ✓ Queued (task_id: {result.id})")
            else:
                # Direct call (testing mode)
                process_ocr(file_id)
                print(f"  ✓ Processed directly")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\nDone! Files are now being reprocessed.")
    print("Check the Process page to see workflow badges update.")

if __name__ == '__main__':
    main()
