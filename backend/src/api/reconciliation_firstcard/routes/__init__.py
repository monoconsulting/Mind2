# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Route modules for FirstCard invoice reconciliation.

This package organizes reconciliation endpoints into separate modules:
- log: Detailed workflow and AI processing logs
- upload: Invoice file uploads and JSON imports
- status: Processing status and invoice details
- lines: Line item listing and candidate matching
- matching: Automatic and manual line-to-receipt matching
- statements: Statement listing, deletion, workflow control

All routes are registered with the recon_bp blueprint.
"""

from __future__ import annotations

# Import all route modules to register them with the blueprint
from . import log, upload, status, lines, matching, statements

__all__ = [
    "log",
    "upload",
    "status",
    "lines",
    "matching",
    "statements",
]
