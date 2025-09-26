#!/usr/bin/env python3
"""
Test script to fetch and display complete file information
including tags, location, file category, and all metadata
"""

import os
import sys
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

# Configure database connection
os.environ['DB_HOST'] = os.getenv('DB_HOST', 'mysql')
os.environ['DB_PORT'] = os.getenv('DB_PORT', '3306')
os.environ['DB_USER'] = os.getenv('DB_USER', 'root')
os.environ['DB_PASSWORD'] = os.getenv('DB_PASSWORD', 'root')
os.environ['DB_DATABASE'] = os.getenv('DB_DATABASE', 'mono_se_db_9')

from services.db.connection import db_cursor


def fetch_file_information(file_id: str):
    """
    Fetch complete information about a file including:
    - Basic file data from unified_files
    - File category details
    - Location data
    - Tags
    """
    result = {}

    with db_cursor() as cur:
        # Fetch basic file information with category
        cur.execute("""
            SELECT
                uf.id,
                uf.file_type,
                uf.created_at,
                uf.updated_at,
                uf.merchant_name,
                uf.orgnr,
                uf.purchase_datetime,
                uf.gross_amount,
                uf.net_amount,
                uf.ai_status,
                uf.ai_confidence,
                uf.submitted_by,
                uf.original_filename,
                uf.file_category,
                uf.file_suffix,
                fc.name as category_name,
                fc.description as category_description
            FROM unified_files uf
            LEFT JOIN file_categories fc ON uf.file_category = fc.id
            WHERE uf.id = %s
        """, (file_id,))

        row = cur.fetchone()
        if not row:
            return None

        result['file_info'] = {
            'id': row[0],
            'file_type': row[1],
            'created_at': row[2].isoformat() if row[2] else None,
            'updated_at': row[3].isoformat() if row[3] else None,
            'merchant_name': row[4],
            'orgnr': row[5],
            'purchase_datetime': row[6].isoformat() if row[6] else None,
            'gross_amount': float(row[7]) if row[7] else None,
            'net_amount': float(row[8]) if row[8] else None,
            'ai_status': row[9],
            'ai_confidence': row[10],
            'submitted_by': row[11],
            'original_filename': row[12],
            'file_suffix': row[14],
            'file_category': {
                'id': row[13],
                'name': row[15],
                'description': row[16]
            } if row[13] else None
        }

        # Fetch location data
        cur.execute("""
            SELECT lat, lon, acc, created_at
            FROM file_locations
            WHERE file_id = %s
        """, (file_id,))

        location = cur.fetchone()
        if location:
            result['location'] = {
                'lat': float(location[0]),
                'lon': float(location[1]),
                'acc': float(location[2]) if location[2] else None,
                'created_at': location[3].isoformat() if location[3] else None
            }

        # Fetch tags
        cur.execute("""
            SELECT
                ft.tag,
                t.description,
                tc.tag_category_name,
                tc.tag_category_description
            FROM file_tags ft
            LEFT JOIN tags t ON ft.tag = t.name
            LEFT JOIN tag_categories tc ON t.tag_category = tc.id
            WHERE ft.file_id = %s
        """, (file_id,))

        tags = []
        for tag_row in cur.fetchall():
            tags.append({
                'tag': tag_row[0],
                'description': tag_row[1],
                'category_name': tag_row[2],
                'category_description': tag_row[3]
            })

        if tags:
            result['tags'] = tags

    return result


def test_all_files():
    """
    Test fetching information for all recently imported files
    """
    print("\n" + "="*80)
    print("COMPLETE FILE INFORMATION TEST")
    print("="*80 + "\n")

    with db_cursor() as cur:
        # Get list of recently imported files
        cur.execute("""
            SELECT id, original_filename
            FROM unified_files
            WHERE file_type = 'receipt'
            ORDER BY created_at DESC
            LIMIT 10
        """)

        files = cur.fetchall()

        if not files:
            print("No files found in database!")
            return

        print(f"Found {len(files)} files. Testing each one:\n")

        for file_id, filename in files:
            print(f"\n{'='*60}")
            print(f"File: {filename or 'Unknown'} (ID: {file_id})")
            print(f"{'='*60}")

            info = fetch_file_information(file_id)

            if info:
                # Display file info
                print("\n📄 BASIC FILE INFO:")
                file_data = info['file_info']
                print(f"  - Type: {file_data['file_type']}")
                print(f"  - Original filename: {file_data['original_filename']}")
                print(f"  - File suffix: {file_data['file_suffix']}")
                print(f"  - Created: {file_data['created_at']}")
                print(f"  - AI Status: {file_data['ai_status']}")

                # Display category
                if file_data['file_category']:
                    print(f"\n📁 FILE CATEGORY:")
                    cat = file_data['file_category']
                    print(f"  - Category: {cat['name']} ({cat['description']})")
                else:
                    print("\n📁 FILE CATEGORY: None")

                # Display merchant info
                if file_data['merchant_name'] or file_data['orgnr']:
                    print(f"\n🏪 MERCHANT INFO:")
                    if file_data['merchant_name']:
                        print(f"  - Name: {file_data['merchant_name']}")
                    if file_data['orgnr']:
                        print(f"  - Org Nr: {file_data['orgnr']}")
                    if file_data['purchase_datetime']:
                        print(f"  - Purchase Date: {file_data['purchase_datetime']}")

                # Display amounts
                if file_data['gross_amount'] or file_data['net_amount']:
                    print(f"\n💰 AMOUNTS:")
                    if file_data['gross_amount']:
                        print(f"  - Gross: {file_data['gross_amount']:.2f}")
                    if file_data['net_amount']:
                        print(f"  - Net: {file_data['net_amount']:.2f}")

                # Display location
                if 'location' in info:
                    print(f"\n📍 LOCATION:")
                    loc = info['location']
                    print(f"  - Latitude: {loc['lat']}")
                    print(f"  - Longitude: {loc['lon']}")
                    if loc['acc']:
                        print(f"  - Accuracy: {loc['acc']}m")
                else:
                    print(f"\n📍 LOCATION: None")

                # Display tags
                if 'tags' in info and info['tags']:
                    print(f"\n🏷️  TAGS ({len(info['tags'])} tags):")
                    for tag in info['tags']:
                        print(f"  - {tag['tag']}")
                        if tag['description']:
                            print(f"    Description: {tag['description']}")
                        if tag['category_name']:
                            print(f"    Category: {tag['category_name']}")
                else:
                    print(f"\n🏷️  TAGS: None")
            else:
                print("ERROR: Could not fetch file information!")

        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80 + "\n")


if __name__ == "__main__":
    test_all_files()