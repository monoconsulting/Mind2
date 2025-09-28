#!/usr/bin/env python3
"""
Simple script to test OCR on a single receipt
"""

import requests
import json
import time
import os

# API base URL
BASE_URL = "http://localhost:8008/ai/api"
TOKEN = None

def authenticate():
    """Authenticate and get JWT token"""
    global TOKEN

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
            return False
    except Exception as e:
        print(f"Authentication error: {e}")
        return False

def check_receipt_ocr_status(receipt_id):
    """Check the OCR status of a receipt"""
    try:
        response = requests.get(f"{BASE_URL}/receipts/{receipt_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"Receipt {receipt_id}:")
            print(f"  Status: {data.get('ai_status', 'unknown')}")
            print(f"  Merchant: {data.get('merchant', 'N/A')}")
            print(f"  OCR Raw Available: {'Yes' if data.get('ocr_raw') else 'No'}")
            if data.get('ocr_raw'):
                print(f"  OCR Text length: {len(data.get('ocr_raw', ''))}")
                print(f"  OCR Preview: {data.get('ocr_raw', '')[:100]}...")
            print(f"  Full response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Failed to check receipt: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error checking receipt: {e}")
        return False

def main():
    print("=== OCR Test ===")

    # Authenticate
    if not authenticate():
        print("Failed to authenticate")
        return

    # Check specific receipt that should have OCR data
    receipt_id = "0ac43f53-6dd9-4e92-b3dd-538716b31108"
    print(f"\nChecking receipt ID: {receipt_id}")
    check_receipt_ocr_status(receipt_id)

if __name__ == "__main__":
    main()
