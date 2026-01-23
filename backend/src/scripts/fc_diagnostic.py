# -*- coding: utf-8 -*-
"""
FC Diagnostic Script - Investigates FC_2504.pdf state in database

Run from backend container:
    python -c "from scripts.fc_diagnostic import run_diagnostic; run_diagnostic()"
Or:
    docker exec -it mind2-ai-api-1 python -c "import sys; sys.path.insert(0, '/app'); from scripts.fc_diagnostic import run_diagnostic; run_diagnostic()"
"""

import json
from typing import Any, Optional


def run_diagnostic():
    """Run full diagnostic on FC_2504.pdf"""
    try:
        from services.db.connection import db_cursor
    except ImportError:
        print("ERROR: Cannot import db_cursor")
        return

    if db_cursor is None:
        print("ERROR: db_cursor is None")
        return

    print("=" * 80)
    print("FC DIAGNOSTIC: Investigating FC_2504.pdf")
    print("=" * 80)

    # Step B1: Find the file in unified_files
    print("\n--- STEP B1: Searching unified_files for FC_2504.pdf ---")
    unified_file_data = None
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, file_type, workflow_type, ai_status, process_status,
                       workflow_run_id, content_hash, deleted_at, created_at, updated_at,
                       original_filename, original_file_name
                FROM unified_files
                WHERE original_filename LIKE '%FC_2504%'
                   OR original_file_name LIKE '%FC_2504%'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()

            if not rows:
                print("  No results found by filename. Trying other_data...")
                cur.execute("""
                    SELECT id, file_type, workflow_type, ai_status, process_status,
                           workflow_run_id, content_hash, deleted_at, created_at, updated_at,
                           original_filename, original_file_name
                    FROM unified_files
                    WHERE other_data LIKE '%FC_2504%'
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()

            if rows:
                print(f"  Found {len(rows)} file(s):")
                for row in rows:
                    print(f"\n  File ID: {row[0]}")
                    print(f"    file_type: {row[1]}")
                    print(f"    workflow_type: {row[2]}")
                    print(f"    ai_status: {row[3]}")
                    print(f"    process_status: {row[4]}")
                    print(f"    workflow_run_id: {row[5]}")
                    print(f"    content_hash: {row[6][:16] if row[6] else None}...")
                    print(f"    deleted_at: {row[7]}")
                    print(f"    created_at: {row[8]}")
                    print(f"    updated_at: {row[9]}")
                    print(f"    original_filename: {row[10]}")
                    print(f"    original_file_name: {row[11]}")
                    if row[7] is None:  # Not deleted
                        unified_file_data = row
            else:
                print("  No unified_files found for FC_2504")
    except Exception as e:
        print(f"  ERROR: {e}")

    if not unified_file_data:
        # Try to find by known ID from logs
        print("\n  Trying known ID from logs: f06df9be-4951-4bbe-a86e-8e85a1031e99")
        try:
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, file_type, workflow_type, ai_status, process_status,
                           workflow_run_id, content_hash, deleted_at, created_at, updated_at,
                           original_filename, original_file_name
                    FROM unified_files
                    WHERE id = 'f06df9be-4951-4bbe-a86e-8e85a1031e99'
                """)
                row = cur.fetchone()
                if row:
                    unified_file_data = row
                    print(f"  Found file by ID!")
                    print(f"    deleted_at: {row[7]}")
                    print(f"    ai_status: {row[3]}")
        except Exception as e:
            print(f"  ERROR: {e}")

    file_id = unified_file_data[0] if unified_file_data else 'f06df9be-4951-4bbe-a86e-8e85a1031e99'

    # Step B2: Find invoice_documents for this file
    print(f"\n--- STEP B2: Searching invoice_documents for file_id={file_id} ---")
    invoice_doc_data = None
    try:
        with db_cursor() as cur:
            # First check by id
            cur.execute("""
                SELECT id, invoice_type, status, processing_status, deleted_at,
                       period_start, period_end, uploaded_at, source_file_id,
                       metadata_json
                FROM invoice_documents
                WHERE id = %s
            """, (file_id,))
            row = cur.fetchone()

            if row:
                invoice_doc_data = row
                print(f"  Found invoice_documents by id={file_id}:")
                print(f"    invoice_type: {row[1]}")
                print(f"    status: {row[2]}")
                print(f"    processing_status: {row[3]}")
                print(f"    deleted_at: {row[4]}")
                print(f"    period_start: {row[5]}")
                print(f"    period_end: {row[6]}")
                print(f"    source_file_id: {row[8]}")
                if row[9]:
                    try:
                        meta = json.loads(row[9]) if isinstance(row[9], str) else json.loads(row[9].decode('utf-8'))
                        print(f"    metadata keys: {list(meta.keys())}")
                    except:
                        print(f"    metadata: (parse error)")
            else:
                print(f"  No invoice_documents found with id={file_id}")

                # Try source_file_id
                cur.execute("""
                    SELECT id, invoice_type, status, processing_status, deleted_at,
                           source_file_id
                    FROM invoice_documents
                    WHERE source_file_id = %s
                """, (file_id,))
                row = cur.fetchone()
                if row:
                    print(f"  Found invoice_documents by source_file_id:")
                    print(f"    id: {row[0]}")
                    print(f"    invoice_type: {row[1]}")
                    print(f"    status: {row[2]}")
                    print(f"    processing_status: {row[3]}")
                    print(f"    deleted_at: {row[4]}")
                    invoice_doc_data = row
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step B2b: Check invoice_lines
    print(f"\n--- STEP B2b: Counting invoice_lines for invoice_id={file_id} ---")
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN match_status IN ('auto', 'manual', 'confirmed') THEN 1 ELSE 0 END)
                FROM invoice_lines
                WHERE invoice_id = %s
            """, (file_id,))
            row = cur.fetchone()
            total = row[0] or 0
            matched = row[1] or 0
            print(f"  Total lines: {total}")
            print(f"  Matched lines: {matched}")

            if total > 0:
                cur.execute("""
                    SELECT id, transaction_date, amount, merchant_name, match_status, matched_file_id
                    FROM invoice_lines
                    WHERE invoice_id = %s
                    LIMIT 5
                """, (file_id,))
                print("  Sample lines:")
                for line in cur.fetchall() or []:
                    print(f"    Line {line[0]}: date={line[1]}, amt={line[2]}, merchant={line[3]}, status={line[4]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step B2c: Check creditcard_invoices_main
    print(f"\n--- STEP B2c: Checking creditcard_invoices_main ---")
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, card_name, invoice_date, due_date, amount_to_pay, file_id
                FROM creditcard_invoices_main
                WHERE file_id = %s
                LIMIT 3
            """, (file_id,))
            rows = cur.fetchall()
            if rows:
                print(f"  Found {len(rows)} main record(s):")
                for row in rows:
                    print(f"    main_id={row[0]}, card={row[1]}, invoice_date={row[2]}, amount={row[4]}")

                    # Count items
                    cur.execute("""
                        SELECT COUNT(*)
                        FROM creditcard_invoice_items
                        WHERE main_id = %s
                    """, (row[0],))
                    item_count = cur.fetchone()[0]
                    print(f"      -> creditcard_invoice_items count: {item_count}")
            else:
                print(f"  No creditcard_invoices_main found for file_id={file_id}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step B3: Check workflow_runs
    print(f"\n--- STEP B3: Checking workflow_runs for file_id={file_id} ---")
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, workflow_key, status, current_stage, created_at, completed_at
                FROM workflow_runs
                WHERE file_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (file_id,))
            rows = cur.fetchall()
            if rows:
                print(f"  Found {len(rows)} workflow run(s):")
                for row in rows:
                    print(f"    run_id={row[0]}, key={row[1]}, status={row[2]}, stage={row[3]}, created={row[4]}")
            else:
                print(f"  No workflow_runs found")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step B3b: Call list_statements API equivalent query
    print(f"\n--- STEP B3b: Simulating list_statements query ---")
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, invoice_type, status, processing_status, deleted_at
                FROM invoice_documents
                WHERE invoice_type IN ('company_card', 'credit_card_invoice')
                  AND deleted_at IS NULL
                ORDER BY uploaded_at DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
            print(f"  Visible statements (deleted_at IS NULL): {len(rows)}")
            for row in rows:
                print(f"    id={row[0]}, type={row[1]}, status={row[2]}, proc={row[3]}")

            # Count all including deleted
            cur.execute("""
                SELECT COUNT(*), SUM(CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END)
                FROM invoice_documents
                WHERE invoice_type IN ('company_card', 'credit_card_invoice')
            """)
            row = cur.fetchone()
            print(f"  Total FC invoice_documents: {row[0]}, non-deleted: {row[1]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_diagnostic()
