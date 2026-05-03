"""
store.py  —  Multi-user, thread-safe storage manager for captured API batches.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ── Directory ─────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

INDEX_FILE = STORAGE_DIR / "index.json"

# ── Batch status values ───────────────────────────────────────────────────────

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_ERROR = "error"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _new_batch_id() -> str:
    """Return a collision-free 16-char hex string."""
    return uuid.uuid4().hex[:16]


def _slugify(url: str) -> str:
    try:
        path = urlparse(url).path
    except Exception:
        path = url
    slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
    return slug[:50] or "api"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── BatchStore ────────────────────────────────────────────────────────────────


class BatchStore:
    """Central storage manager. One instance shared across all threads."""

    def __init__(self, storage_dir: Path = STORAGE_DIR) -> None:
        self._dir = storage_dir
        self._dir.mkdir(exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._index_lock = threading.Lock()
        self._batch_locks: dict[str, threading.Lock] = {}
        self._batch_locks_lock = threading.Lock()
        self._live: dict[str, dict] = {}
        self._live_lock = threading.Lock()

    def _lock_for(self, batch_id: str) -> threading.Lock:
        with self._batch_locks_lock:
            if batch_id not in self._batch_locks:
                self._batch_locks[batch_id] = threading.Lock()
            return self._batch_locks[batch_id]

    def _read_index(self) -> dict[str, dict]:
        if not self._index_path.exists():
            return {}
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_index(self, index: dict) -> None:
        self._index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def _update_index(self, batch_id: str, **fields) -> None:
        with self._index_lock:
            index = self._read_index()
            entry = index.setdefault(batch_id, {"batch_id": batch_id})
            entry.update(fields)
            self._write_index(index)

    def create_batch(
        self,
        body: dict,
        requests_list: list[dict],
        filter_report: dict,
        client_ip: str = "unknown",
    ) -> str:
        batch_id = _new_batch_id()
        batch_dir = self._dir / batch_id
        batch_dir.mkdir(exist_ok=True)

        capture_data = dict(
            body,
            batch_id=batch_id,
            created_at=_now_iso(),
            client_ip=client_ip,
            requests=requests_list,
            total=len(requests_list),
        )
        (batch_dir / "capture.json").write_text(json.dumps(capture_data, indent=2), encoding="utf-8")

        for i, req in enumerate(requests_list):
            method = (req.get("method") or "UNKNOWN").upper()
            slug = _slugify(req.get("url", ""))
            fname = batch_dir / f"{i:02d}_{method}_{slug}.json"
            fname.write_text(json.dumps(req, indent=2), encoding="utf-8")

        live_entry: dict[str, Any] = {
            "batch_id": batch_id,
            "status": STATUS_PENDING,
            "message": "Queued - starting shortly...",
            "created_at": capture_data["created_at"],
            "client_ip": client_ip,
            "progress": {"done": 0, "total": len(requests_list)},
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "filter": filter_report,
            "groups": [],
            "error": None,
        }
        with self._live_lock:
            self._live[batch_id] = live_entry

        self._update_index(
            batch_id,
            **{
                "status": STATUS_PENDING,
                "created_at": capture_data["created_at"],
                "client_ip": client_ip,
                "total": len(requests_list),
                "filter": filter_report,
            },
        )

        return batch_id

    def set_status(self, batch_id: str, **fields) -> None:
        with self._live_lock:
            if batch_id in self._live:
                self._live[batch_id].update(fields)

    def get(self, batch_id: str) -> dict | None:
        with self._live_lock:
            entry = self._live.get(batch_id)
            return dict(entry) if entry else None

    def get_from_disk(self, batch_id: str) -> dict | None:
        batch_dir = self._dir / batch_id
        results_path = batch_dir / "results.json"
        capture_path = batch_dir / "capture.json"

        for path in (results_path, capture_path):
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
        return None

    def finalise(self, batch_id: str) -> None:
        with self._lock_for(batch_id):
            with self._live_lock:
                final = dict(self._live.get(batch_id, {}))

            if not final:
                return

            batch_dir = self._dir / batch_id
            batch_dir.mkdir(exist_ok=True)
            (batch_dir / "results.json").write_text(json.dumps(final, indent=2), encoding="utf-8")

        summary = final.get("summary", {})
        self._update_index(
            batch_id,
            **{
                "status": final.get("status", STATUS_DONE),
                "completed_at": _now_iso(),
                "summary": summary,
            },
        )

    def list_batches(self, limit: int = 100) -> list[dict]:
        with self._index_lock:
            index = self._read_index()

        entries = list(index.values())
        entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)

        with self._live_lock:
            for entry in entries:
                bid = entry.get("batch_id")
                if bid and bid in self._live:
                    live = self._live[bid]
                    entry["status"] = live.get("status", entry.get("status"))
                    entry["summary"] = live.get("summary", entry.get("summary"))
                    entry["progress"] = live.get("progress")

        return entries[:limit]

    def batch_dir(self, batch_id: str) -> Path:
        return self._dir / batch_id

    def cleanup(self, max_age_days: int = 7) -> int:
        import shutil

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
        removed = 0

        with self._index_lock:
            index = self._read_index()
            to_remove = []

            for batch_id, meta in index.items():
                created = meta.get("created_at", "")
                try:
                    created_dt = datetime.fromisoformat(created)
                except (ValueError, TypeError):
                    continue
                if created_dt < cutoff:
                    to_remove.append(batch_id)

            for batch_id in to_remove:
                batch_dir = self._dir / batch_id
                if batch_dir.exists():
                    shutil.rmtree(batch_dir, ignore_errors=True)
                del index[batch_id]
                with self._live_lock:
                    self._live.pop(batch_id, None)
                with self._batch_locks_lock:
                    self._batch_locks.pop(batch_id, None)
                removed += 1

            if to_remove:
                self._write_index(index)

        return removed

    def recover_from_disk(self) -> int:
        recovered = 0
        with self._index_lock:
            index = self._read_index()

        for batch_id, meta in index.items():
            status = meta.get("status")
            if status in (STATUS_DONE, STATUS_ERROR):
                batch_dir = self._dir / batch_id
                results_path = batch_dir / "results.json"
                if results_path.exists():
                    try:
                        data = json.loads(results_path.read_text(encoding="utf-8"))
                        with self._live_lock:
                            if batch_id not in self._live:
                                self._live[batch_id] = data
                                recovered += 1
                    except (json.JSONDecodeError, OSError):
                        pass

        return recovered


store = BatchStore()
