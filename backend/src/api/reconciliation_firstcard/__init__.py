# -*- coding: utf-8 -*-
"""
FirstCard Reconciliation API Module

Refactored from monolithic reconciliation_firstcard.py into modular structure.
Maintains full backwards compatibility with existing API contracts.

Kontrollrad: ÅÄÖ åäö – Swedish encoding test
"""

from flask import Blueprint

# Create the blueprint
recon_bp = Blueprint("reconciliation_firstcard", __name__)

def register_routes() -> None:
    # Import routes lazily to avoid circular imports during Celery startup.
    from . import routes  # noqa: F401, E402

__all__ = ["recon_bp", "register_routes"]
