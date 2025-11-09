# -*- coding: utf-8 -*-
# ÅÄÖ åäö – Swedish encoding test

"""Utility functions for FirstCard reconciliation.

This module exports database helpers and utility functions used throughout
the FirstCard reconciliation system.
"""

from .db_helpers import (
    _as_date,
    _count_invoice_lines,
    _create_invoice_document,
    _create_workflow_run,
    _ensure_processing_state,
    _find_file_id_by_hash,
    _find_invoice_id_for_main,
    _find_invoice_line_id_for_item,
    _list_invoice_files,
    _load_invoice_document,
    _log_line_history,
    _storage,
    _write_invoice_metadata,
)

# Export with and without underscore prefix for compatibility
as_date = _as_date
count_invoice_lines = _count_invoice_lines
create_invoice_document = _create_invoice_document
create_workflow_run = _create_workflow_run
ensure_processing_state = _ensure_processing_state
find_file_id_by_hash = _find_file_id_by_hash
find_invoice_id_for_main = _find_invoice_id_for_main
find_invoice_line_id_for_item = _find_invoice_line_id_for_item
list_invoice_files = _list_invoice_files
load_invoice_document = _load_invoice_document
log_line_history = _log_line_history
storage = _storage
write_invoice_metadata = _write_invoice_metadata

__all__ = [
    # With underscore (original names)
    "_as_date",
    "_count_invoice_lines",
    "_create_invoice_document",
    "_create_workflow_run",
    "_ensure_processing_state",
    "_find_file_id_by_hash",
    "_find_invoice_id_for_main",
    "_find_invoice_line_id_for_item",
    "_list_invoice_files",
    "_load_invoice_document",
    "_log_line_history",
    "_storage",
    "_write_invoice_metadata",
    # Without underscore (clean API)
    "as_date",
    "count_invoice_lines",
    "create_invoice_document",
    "create_workflow_run",
    "ensure_processing_state",
    "find_file_id_by_hash",
    "find_invoice_id_for_main",
    "find_invoice_line_id_for_item",
    "list_invoice_files",
    "load_invoice_document",
    "log_line_history",
    "storage",
    "write_invoice_metadata",
]
