#!/usr/bin/env python3
"""
Script to trigger WF1_RECEIPT workflows for uploaded PDF pages via API.
"""

import requests
import time

API_BASE = "http://localhost:8008/ai/api"

# Step 1: Login and get token
print("Logging in...")
login_response = requests.post(
    f"{API_BASE}/auth/login",
    json={"username": "admin", "password": "adminadmin"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    exit(1)

token = login_response.json().get("access_token")
print(f"Got token: {token[:30]}...\n")

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Get all receipts with uploaded status
print("Fetching uploaded files...")
receipts_response = requests.get(
    f"{API_BASE}/receipts?page_size=100",
    headers=headers
)

if receipts_response.status_code != 200:
    print(f"Failed to fetch receipts: {receipts_response.status_code}")
    exit(1)

items = receipts_response.json().get("items", [])
uploaded_files = [
    item for item in items
    if item.get("ai_status") == "uploaded" and item.get("file_type") == "pdf_page"
]

print(f"Found {len(uploaded_files)} uploaded PDF pages\n")

if not uploaded_files:
    print("No files to process.")
    exit(0)

# Step 3: Resume processing for each file
success_count = 0
fail_count = 0

for i, file_data in enumerate(uploaded_files, 1):
    file_id = file_data["id"]
    filename = file_data.get("original_filename", "unknown")

    print(f"[{i}/{len(uploaded_files)}] {filename[:50]} ({file_id[:8]}...)...", end=" ")

    response = requests.post(
        f"{API_BASE}/ingest/process/{file_id}/resume",
        headers=headers
    )

    if response.status_code == 200:
        print("OK")
        success_count += 1
    else:
        print(f"FAIL ({response.status_code})")
        fail_count += 1

    time.sleep(0.05)  # Small delay

print(f"\n=== Summary ===")
print(f"Success: {success_count}")
print(f"Failed: {fail_count}")
print(f"Total: {len(uploaded_files)}")
