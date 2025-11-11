from __future__ import annotations

import sys
from types import ModuleType
from typing import Any


def _tasks_module() -> ModuleType | None:
    """Return the canonical services.tasks module if it is loaded."""

    return sys.modules.get("services.tasks")


def get_override(name: str, default: Any) -> Any:
    """Return the patched attribute from services.tasks if present."""

    module = _tasks_module()
    if module is None:
        return default
    return getattr(module, name, default)
