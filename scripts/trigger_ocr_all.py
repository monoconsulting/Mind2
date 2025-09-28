#!/usr/bin/env python3
"""
Script to trigger OCR processing for all existing receipts
"""

import requests
import json
import time
import sys
import os

# API base URL
BASE_URL = "http://localhost:8008/ai/api"
TOKEN = None

def authenticate():
    """Authenticate and get JWT token"""
    global TOKEN

    # Try to get admin password from environment or use default
    admin_password = os.getenv("ADMIN_PASSWORD", "adminadmin")

    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin", "password": admin_password, "hours": 1}
        )
        if response.status_code == 200:
            data = response.json()
            TOKEN = data.get('access_token')
            print("Authentication successful")
            return True
        else:
            print(f"Authentication failed: {response.status_code}")
            if response.status_code == 401:
                print("Check that ADMIN_PASSWORD is correct in .env file")
            return False
    except Exception as e:
        print(f"Authentication error: {e}")
        return False

def get_all_receipts():
    """Fetch all receipts from the API"""
    try:
        # Get receipts with a large page size to get all of them
        response = requests.get(f"{BASE_URL}/receipts?page_size=1000")
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
        else:
            print(f"Failed to fetch receipts: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching receipts: {e}")
        return []

def trigger_ocr_for_receipt(receipt_id):
    """Trigger OCR for a specific receipt"""
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        response = requests.post(f"{BASE_URL}/ingest/process/{receipt_id}/ocr", headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result.get('queued'):
                return True, result.get('task_id')
            else:
                return False, "Not queued"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("="*60)
    print("MIND OCR Processing Tool")
    print("="*60)

    # First authenticate
    if not authenticate():
        print("Failed to authenticate. Exiting.")
        print("Make sure the backend is running and ADMIN_PASSWORD is set correctly.")
        sys.exit(1)

    print("\nFetching all receipts...")
    receipts = get_all_receipts()

    if not receipts:
        print("No receipts found or couldn't fetch receipts")
        print("Make sure there are receipts in the system.")
        return

    print(f"Found {len(receipts)} receipts")

    # Ask for confirmation
    response = input(f"\nDo you want to trigger OCR for all {len(receipts)} receipts? (y/n): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return

    successful = 0
    failed = 0
    skipped = 0

    print("\nProcessing receipts...\n")
    for i, receipt in enumerate(receipts, 1):
        receipt_id = receipt.get('id')
        if not receipt_id:
            print(f"[{i}/{len(receipts)}] Skipping receipt without ID")
            skipped += 1
            continue

        # Check if OCR might already be done (if ai_status is 'completed')
        ai_status = receipt.get('ai_status', '').lower()
        if ai_status == 'completed':
            print(f"[{i}/{len(receipts)}] Receipt {receipt_id[:8]}... already processed (skipping)")
            skipped += 1
            continue

        print(f"[{i}/{len(receipts)}] Processing receipt {receipt_id[:8]}...", end=" ")

        success, result = trigger_ocr_for_receipt(receipt_id)

        if success:
            print(f"OK - Queued (task: {result[:8]}...)")
            successful += 1
        else:
            print(f"FAILED - {result}")
            failed += 1

        # Small delay to avoid overwhelming the server
        time.sleep(0.1)

    print(f"\n{'='*60}")
    print(f"OCR Processing Summary:")
    print(f"  Total receipts: {len(receipts)}")
    print(f"  Successfully queued: {successful}")
    print(f"  Already processed/skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"{'='*60}")

    if successful > 0:
        print(f"\n{successful} OCR tasks have been queued and are being processed.")
        print("Check the receipts page to see the results once processing is complete.")

if __name__ == "__main__":
    main()