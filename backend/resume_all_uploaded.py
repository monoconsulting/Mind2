#!/usr/bin/env python3
"""
Script to resume processing for all files with status 'uploaded'.
This triggers the AI processing workflow for files that were uploaded but never processed.
"""

import requests
import sys
import time

API_BASE = "http://localhost:8008/ai/api"

def get_uploaded_files():
    """Fetch all files with 'uploaded' status."""
    response = requests.get(f"{API_BASE}/receipts?page_size=100")
    if response.status_code != 200:
        print(f"Error fetching receipts: {response.status_code}")
        return []

    data = response.json()
    items = data.get("items", [])
    uploaded = [item for item in items if item.get("ai_status") == "uploaded"]
    return uploaded

def resume_file(file_id):
    """Resume processing for a single file."""
    response = requests.post(f"{API_BASE}/ingest/process/{file_id}/resume")
    if response.status_code != 200:
        try:
            print(f" (Status: {response.status_code}, Response: {response.text[:100]})")
        except:
            print(f" (Status: {response.status_code})")
    return response.status_code == 200

def main():
    print("Fetching files with 'uploaded' status...")
    uploaded_files = get_uploaded_files()

    if not uploaded_files:
        print("No files with 'uploaded' status found.")
        return

    print(f"Found {len(uploaded_files)} files to resume")

    success_count = 0
    fail_count = 0

    for i, file_data in enumerate(uploaded_files, 1):
        file_id = file_data["id"]
        filename = file_data.get("original_filename", "unknown")

        print(f"[{i}/{len(uploaded_files)}] Resuming {filename} ({file_id[:8]}...)...", end=" ")

        if resume_file(file_id):
            print("OK")
            success_count += 1
        else:
            print("FAIL")
            fail_count += 1

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    print(f"\n=== Summary ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {len(uploaded_files)}")

if __name__ == "__main__":
    main()
