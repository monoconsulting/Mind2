#!/usr/bin/env python3
"""Run migration 0025 to update AI prompt titles"""

import mysql.connector
import os
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3310,
    'user': 'minduser',
    'password': 'mind2password',
    'database': 'mono_se_db_9'
}

def run_migration():
    migration_file = Path(__file__).parent / 'database' / 'migrations' / '0025_update_ai_prompt_titles.sql'

    if not migration_file.exists():
        print(f"Migration file not found: {migration_file}")
        return

    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split by semicolon and filter out comments and empty statements
    statements = [
        stmt.strip()
        for stmt in sql_content.split(';')
        if stmt.strip() and not stmt.strip().startswith('--')
    ]

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        for stmt in statements:
            if stmt:
                print(f"Executing: {stmt[:80]}...")
                cursor.execute(stmt)

        conn.commit()
        print("✓ Migration 0025 completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    run_migration()
