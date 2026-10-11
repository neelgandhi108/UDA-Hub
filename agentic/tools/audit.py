"""Structured JSON Lines audit logging."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonlAuditLogger:
    """Append safe, searchable events as one JSON object per line."""

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log(
        self,
        event: str,
        agent: str,
        *,
        thread_id: str = "unknown",
        ticket_id: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "agent": agent,
            "thread_id": str(thread_id),
            "ticket_id": str(ticket_id),
            "details": details or {},
        }
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


class NullAuditLogger:
    """Drop-in logger used when callers explicitly disable file logging."""

    def log(self, *args, **kwargs) -> None:
        return None
