#!/usr/bin/env python3
"""
Check status of receipts in the system.
"""

import requests
import sys

API_BASE = "http://localhost:8008/ai/api"

# Login
login_response = requests.post(
    f"{API_BASE}/auth/login",
    json={"username": "admin", "password": "adminadmin"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    sys.exit(1)

token = login_response.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Get receipts
receipts_response = requests.get(
    f"{API_BASE}/receipts?page_size=100",
    headers=headers
)

if receipts_response.status_code != 200:
    print(f"Failed to fetch receipts: {receipts_response.status_code}")
    sys.exit(1)

items = receipts_response.json().get("items", [])

# Group by status
by_status = {}
for item in items:
    status = item.get("ai_status", "unknown")
    if status not in by_status:
        by_status[status] = []
    by_status[status].append(item)

# Print summary
print("=== Receipt Status Summary ===")
for status, files in sorted(by_status.items()):
    print(f"\n{status}: {len(files)} files")
    for i, f in enumerate(files[:5], 1):
        filename = f.get("original_filename", "unknown")
        file_type = f.get("file_type", "unknown")
        file_id = f.get("id", "unknown")
        print(f"  {i}. {filename[:50]} ({file_type}) - {file_id[:8]}...")

# Check for specific PDF pages
pdf_pages = [item for item in items if item.get("file_type") == "pdf_page"]
print(f"\n=== PDF Pages: {len(pdf_pages)} total ===")
for status in ["uploaded", "processing", "completed", "ai_completed"]:
    count = len([p for p in pdf_pages if p.get("ai_status") == status])
    if count > 0:
        print(f"  {status}: {count}")
