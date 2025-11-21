from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


def _definitions_path() -> Path:
    """Return absolute path to the shared status definition JSON file."""
    return Path(__file__).resolve().parents[2] / "shared" / "status_definitions.json"


@lru_cache(maxsize=1)
def load_status_definitions() -> Dict[str, Any]:
    """
    Load the shared status definition file once per process.

    Returns a dict with keys: categories, stageKeys, legacyStatuses, statusLabels.
    """
    payload: Dict[str, Any] = {"categories": {}, "stageKeys": {}, "legacyStatuses": {}, "statusLabels": {}}
    path = _definitions_path()
    if not path.exists():
        return payload
    try:
        raw = path.read_text(encoding="utf-8")
        parsed: Dict[str, Any] = json.loads(raw)
        if isinstance(parsed, dict):
            payload.update(parsed)
    except Exception:
        # Fall back to empty payload if parsing fails; caller must handle gracefully.
        return payload
    return payload


def get_stage_definitions() -> Dict[str, Dict[str, Any]]:
    """Convenience helper for consumers importing only stage metadata."""
    data = load_status_definitions()
    stage_keys = data.get("stageKeys")
    return stage_keys if isinstance(stage_keys, dict) else {}


def get_legacy_status_definitions() -> Dict[str, Dict[str, Any]]:
    """Return the mapping for legacy ai_status values."""
    data = load_status_definitions()
    legacy = data.get("legacyStatuses")
    return legacy if isinstance(legacy, dict) else {}


def get_status_label_map() -> Dict[str, str]:
    """Return textual translations for workflow stage status values."""
    data = load_status_definitions()
    labels = data.get("statusLabels")
    return labels if isinstance(labels, dict) else {}
