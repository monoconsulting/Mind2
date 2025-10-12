#!/usr/bin/env python3
"""Upload test files to the ingest API."""
import base64
import hmac
import json
import sys
import time
from hashlib import sha256
from pathlib import Path

import requests


def create_jwt(payload: dict, secret: str = "3j8vjsasdvj98evvjdhyugi7d6gvehbcyuBAJCYCBf37hfbfb323nff742048t90583") -> str:
    """Create a simple HS256 JWT token."""
    # Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).decode().rstrip('=')

    # Payload
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')

    # Signature
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def upload_file(filepath: str, api_url: str = "http://localhost:8008/ai/api/ingest/upload"):
    """Upload a file to the ingest API."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        return None

    # Create JWT token (expires in 1 hour)
    payload = {
        "sub": "test-user",
        "exp": int(time.time()) + 3600
    }
    token = create_jwt(payload)

    print(f"Uploading {path.name}...")
    print(f"File size: {path.stat().st_size} bytes")

    with open(path, 'rb') as f:
        files = {'files': (path.name, f, 'application/octet-stream')}
        headers = {
            'Authorization': f'Bearer {token}'
        }

        response = requests.post(api_url, files=files, headers=headers)

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response.json() if response.status_code == 200 else None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_test.py <file_path>")
        sys.exit(1)

    result = upload_file(sys.argv[1])
    if result:
        print(f"Success! Uploaded: {result.get('uploaded')} files")
