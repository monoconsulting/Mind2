from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_json_logging(level: str | int | None = None) -> None:
    lvl = level or os.getenv("LOG_LEVEL", "INFO")
    root = logging.getLogger()
    root.setLevel(lvl)
    # Replace handlers
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
