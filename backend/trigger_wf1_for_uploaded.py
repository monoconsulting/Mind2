#!/usr/bin/env python3
"""
Script to create WF1_RECEIPT workflows for all files with status 'uploaded' by calling the API.
This fixes the issue where PDF pages were created but never processed through the receipt pipeline.
"""

import requests
import json

def get_uploaded_pdf_pages():
    """Get all PDF pages with 'uploaded' status."""
    if db_cursor is None:
        print("Database not available")
        return []

    with db_cursor() as cur:
        cur.execute("""
            SELECT id, original_filename
            FROM unified_files
            WHERE ai_status='uploaded' AND file_type='pdf_page'
            ORDER BY created_at ASC
        """)
        return cur.fetchall()

def trigger_wf1(file_id, filename):
    """Create and dispatch WF1_RECEIPT workflow for a file."""
    try:
        # Create workflow run
        workflow_run_id = create_workflow_run(
            workflow_key="WF1_RECEIPT",
            source_channel="manual_trigger",
            file_id=file_id,
            content_hash=""  # Not critical for resume
        )

        if not workflow_run_id:
            return False, "Failed to create workflow_run"

        # Dispatch the workflow
        success = dispatch_workflow(workflow_run_id)

        if success:
            return True, f"Dispatched WF1 run {workflow_run_id}"
        else:
            return False, "Failed to dispatch workflow"

    except Exception as e:
        return False, str(e)

def main():
    print("Fetching uploaded PDF pages...")
    files = get_uploaded_pdf_pages()

    if not files:
        print("No uploaded PDF pages found.")
        return

    print(f"Found {len(files)} PDF pages to process\n")

    success_count = 0
    fail_count = 0

    for i, (file_id, filename) in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {filename} ({file_id[:8]}...)...", end=" ")

        success, message = trigger_wf1(file_id, filename)

        if success:
            print(f"OK - {message}")
            success_count += 1
        else:
            print(f"FAIL - {message}")
            fail_count += 1

    print(f"\n=== Summary ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {len(files)}")

if __name__ == "__main__":
    main()
