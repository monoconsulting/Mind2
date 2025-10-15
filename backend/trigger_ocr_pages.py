#!/usr/bin/env python3
"""Trigger OCR processing for FC page images."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.db.connection import db_cursor
from services.tasks import process_ocr

def main():
    # Get page image IDs for the FC file
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, original_filename
            FROM unified_files
            WHERE original_file_id = '1f787e7e-f24e-4db6-b66b-ae3f4c5d69d9'
              AND file_type = 'cc_image'
            ORDER BY original_filename
        """)
        pages = cur.fetchall()

    print(f"Found {len(pages)} page images to process:")
    for page_id, filename in pages:
        print(f"  - {filename} ({page_id})")

    print("\nTriggering OCR processing...")
    for page_id, filename in pages:
        try:
            if hasattr(process_ocr, 'delay'):
                result = process_ocr.delay(page_id)
                print(f"  ✓ {filename}: Queued (task_id: {result.id})")
            else:
                process_ocr(page_id)
                print(f"  ✓ {filename}: Processed directly")
        except Exception as e:
            print(f"  ✗ {filename}: Error - {e}")

    print("\nDone! OCR tasks queued. Once all pages complete, AI6 will run automatically.")

if __name__ == '__main__':
    main()
