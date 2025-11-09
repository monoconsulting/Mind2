# -*- coding: utf-8 -*-
"""
FirstCard Reconciliation API (Legacy Wrapper)

DEPRECATED: This file is a compatibility wrapper.
The actual implementation has been refactored into a modular package:
  - backend/src/api/reconciliation_firstcard/

All new code should import directly from the new package:
  from api.reconciliation_firstcard import recon_bp

This wrapper maintains backwards compatibility for existing imports.

Kontrollrad: ÅÄÖ åäö – Swedish encoding test
"""

from __future__ import annotations

# Re-export the refactored blueprint for backwards compatibility
from api.reconciliation_firstcard import recon_bp

__all__ = ["recon_bp"]
