#!/usr/bin/env python3
"""
Run migration 0031: Add ocr_raw to creditcard_invoices_main
"""
import sys
import os

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.db.connection import db_cursor

def run_migration():
    """Execute migration 0031"""
    sql_statements = [
        """
        ALTER TABLE creditcard_invoices_main
        ADD COLUMN IF NOT EXISTS ocr_raw LONGTEXT NULL
        COMMENT 'Merged OCR text from all invoice pages'
        AFTER invoice_number
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_creditcard_invoices_number
        ON creditcard_invoices_main(invoice_number)
        """
    ]

    try:
        with db_cursor() as cur:
            for idx, sql in enumerate(sql_statements, 1):
                sql = sql.strip()
                if sql:
                    print(f"Executing statement {idx}...")
                    cur.execute(sql)
                    print(f"✓ Statement {idx} completed")

        print("\n✓ Migration 0031 completed successfully!")
        return 0

    except Exception as e:
        print(f"\n✗ Migration failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(run_migration())
