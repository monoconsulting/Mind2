#!/usr/bin/env python3
"""Helper script to add workflow_type=creditcard_invoice to FC upload endpoint."""

code = '''
            _insert_unified_file(
                file_id=invoice_id,
                file_type="cc_pdf",
                content_hash=file_hash,
                submitted_by=submitted_by,
                original_filename=safe_name,
                ai_status="uploaded",
                mime_type="application/pdf",
                file_suffix=os.path.splitext(safe_name)[1] or ".pdf",
                original_file_id=invoice_id,
                original_file_name=safe_name,
                original_file_size=len(data),
                other_data={
                    "detected_kind": "pdf",
                    "page_count": len(pages),
                    "source": "invoice_upload",
                },
            )
            # HARD ENFORCEMENT: Set workflow_type to enforce credit card invoice pipeline
            if db_cursor is not None:
                try:
                    with db_cursor() as cur:
                        cur.execute(
                            "UPDATE unified_files SET workflow_type = 'creditcard_invoice' WHERE id = %s",
                            (invoice_id,),
                        )
                except Exception:
                    pass  # Best-effort
            fs.save_original(invoice_id, safe_name, data)

            page_file_ids = []
            for page in pages:
                page_id = str(uuid.uuid4())
                page_number = int(getattr(page, "index", 0)) + 1
                page_hash = hashlib.sha256(page.bytes).hexdigest()
                stored_name = f"page-{page_number:04d}.png"
                original_path = page.path
                _insert_unified_file(
                    file_id=page_id,
                    file_type="cc_image",
                    content_hash=page_hash,
                    submitted_by=submitted_by,
                    original_filename=f"{safe_name}-page-{page_number:04d}.png",
                    ai_status="uploaded",
                    mime_type="image/png",
                    file_suffix=".png",
                    original_file_id=invoice_id,
                    original_file_name=safe_name,
                    original_file_size=len(page.bytes),
                    other_data={
                        "detected_kind": "pdf_page",
                        "page_number": page_number,
                        "source_invoice": invoice_id,
                        "source": "invoice_upload",
                    },
                )
                stored_path = fs.adopt(page_id, stored_name, original_path)
                cleanup_paths.discard(original_path)
                page.path = stored_path
                page_file_ids.append(page_id)
                _queue_ocr(page_id)
                page_refs.append({"file_id": page_id, "page_number": page_number})

            # HARD ENFORCEMENT: Set workflow_type for all page images
            if db_cursor is not None and page_file_ids:
                try:
                    with db_cursor() as cur:
                        placeholders = ', '.join(['%s'] * len(page_file_ids))
                        cur.execute(
                            f"UPDATE unified_files SET workflow_type = 'creditcard_invoice' WHERE id IN ({placeholders})",
                            page_file_ids,
                        )
                except Exception:
                    pass  # Best-effort
'''

print("Add this code to reconciliation_firstcard.py upload_invoice function")
print("Replace lines 294-343 with the updated code that sets workflow_type")
