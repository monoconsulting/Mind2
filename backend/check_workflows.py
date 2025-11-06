#!/usr/bin/env python3
"""
Check workflow runs for processing files.
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

# Get receipts with processing status
receipts_response = requests.get(
    f"{API_BASE}/receipts?page_size=100",
    headers=headers
)

if receipts_response.status_code != 200:
    print(f"Failed to fetch receipts: {receipts_response.status_code}")
    sys.exit(1)

items = receipts_response.json().get("items", [])
processing_files = [item for item in items if item.get("ai_status") == "processing"]

print(f"=== Checking {len(processing_files)} files with 'processing' status ===\n")

for i, file_data in enumerate(processing_files[:10], 1):
    file_id = file_data["id"]
    filename = file_data.get("original_filename", "unknown")
    file_type = file_data.get("file_type", "unknown")

    print(f"{i}. {filename[:50]} ({file_type})")
    print(f"   File ID: {file_id}")

    # Try to get log for this file
    log_response = requests.get(
        f"{API_BASE}/receipts/{file_id}/log",
        headers=headers
    )

    if log_response.status_code == 200:
        log_data = log_response.json()
        workflow_runs = log_data.get("workflow_runs", [])

        if workflow_runs:
            print(f"   Workflows: {len(workflow_runs)}")
            for wr in workflow_runs:
                print(f"     - {wr.get('workflow_key')} (status: {wr.get('status')}, stage: {wr.get('current_stage')})")
        else:
            print("   NO WORKFLOWS FOUND - This is the problem!")
    else:
        print(f"   Failed to fetch log: {log_response.status_code}")

    print()
