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

__all__ = ["recon_bp"]
