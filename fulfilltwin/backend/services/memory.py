from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonMemoryStore:
    """Thread-safe append-only JSON memory with atomic writes."""

    def __init__(self, path: Path, max_records: int = 250) -> None:
        self.path = path
        self.max_records = max_records
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": 1, "runs": []})

    def _read(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
                raise ValueError("Invalid memory schema")
            return payload
        except (json.JSONDecodeError, OSError, ValueError):
            return {"version": 1, "runs": []}

    def _write(self, payload: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp.replace(self.path)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            enriched = {
                **record,
                "stored_at": datetime.now(timezone.utc).isoformat(),
            }
            payload["runs"].append(enriched)
            payload["runs"] = payload["runs"][-self.max_records :]
            self._write(payload)
            return enriched

    def list(self, limit: int = 25) -> list[dict[str, Any]]:
        with self._lock:
            runs = self._read()["runs"]
            return list(reversed(runs[-max(1, limit) :]))

    def latest(self) -> dict[str, Any] | None:
        rows = self.list(limit=1)
        return rows[0] if rows else None

    def approve_run(self, run_id: str, user: str = "Manager") -> dict[str, Any] | None:
        with self._lock:
            payload = self._read()
            for run in payload["runs"]:
                if run.get("run_id") == run_id:
                    if run.get("approval", {}).get("status") == "PENDING":
                        run["approval"]["status"] = "APPROVED"
                        run["approval"]["approved_by"] = user
                        run["approval"]["approved_at"] = datetime.now(timezone.utc).isoformat()
                        self._write(payload)
                        return run
                    return run
            return None

    def clear(self) -> None:
        with self._lock:
            self._write({"version": 1, "runs": []})
