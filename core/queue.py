"""
Download queue manager.
Manages concurrent downloads, queuing, and lifecycle.
Pure Python — no GUI dependency.
Communicates with GUI via callback.
"""

import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from core.models import DownloadItem, DownloadOptions, DownloadStatus
from core.downloader import DownloadEngine


class QueueManager:
    """
    Manages a list of DownloadItems and runs up to `max_concurrent` at a time.
    Thread-safe.
    """

    def __init__(self, on_event: Callable[[Dict[str, Any]], None], max_concurrent: int = 2):
        self._items: Dict[int, DownloadItem] = {}
        self._engines: Dict[int, DownloadEngine] = {}
        self._lock = threading.Lock()
        self._on_event = on_event
        self._max_concurrent = max_concurrent
        self._next_id = 1
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False

    # ── Public API ─────────────────────────────────────────────────────────

    def set_max_concurrent(self, n: int):
        with self._lock:
            self._max_concurrent = max(1, n)

    def add(self, options: DownloadOptions) -> int:
        """Add a new item to the queue. Returns the item ID."""
        with self._lock:
            item_id = self._next_id
            self._next_id += 1
            item = DownloadItem(
                id=item_id,
                options=options,
                status=DownloadStatus.QUEUED,
                created_at=datetime.now(),
            )
            self._items[item_id] = item
        self._emit_item_event(item_id, "item_added")
        self._schedule()
        return item_id

    def start_all(self):
        """Un-pause all paused items and start scheduler."""
        with self._lock:
            for item in self._items.values():
                if item.status == DownloadStatus.PAUSED:
                    item.status = DownloadStatus.QUEUED
        self._schedule()

    def cancel_all(self):
        with self._lock:
            ids = list(self._items.keys())
        for item_id in ids:
            self.cancel(item_id)

    def cancel(self, item_id: int):
        with self._lock:
            item = self._items.get(item_id)
            engine = self._engines.get(item_id)
        if item is None:
            return
        if engine:
            engine.cancel()
        else:
            with self._lock:
                if item.status in (DownloadStatus.QUEUED, DownloadStatus.PAUSED):
                    item.status = DownloadStatus.CANCELLED
            self._emit_item_event(item_id, "cancelled")

    def remove(self, item_id: int):
        """Remove completed/failed/cancelled item from queue."""
        with self._lock:
            self._items.pop(item_id, None)
            self._engines.pop(item_id, None)
        self._emit_item_event(item_id, "item_removed")

    def clear_completed(self):
        with self._lock:
            done = [
                i for i, item in self._items.items()
                if item.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED)
            ]
        for i in done:
            self.remove(i)

    def retry(self, item_id: int):
        with self._lock:
            item = self._items.get(item_id)
            if item and item.status in (DownloadStatus.FAILED, DownloadStatus.CANCELLED):
                item.status = DownloadStatus.QUEUED
                item.progress = 0
                item.error_msg = ""
        self._schedule()

    def get_items(self) -> List[DownloadItem]:
        with self._lock:
            return list(self._items.values())

    def get_item(self, item_id: int) -> Optional[DownloadItem]:
        with self._lock:
            return self._items.get(item_id)

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            items = list(self._items.values())
        return {
            "queued": sum(1 for i in items if i.status == DownloadStatus.QUEUED),
            "active": sum(1 for i in items if i.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PROCESSING, DownloadStatus.PREPARING)),
            "completed": sum(1 for i in items if i.status == DownloadStatus.COMPLETED),
            "failed": sum(1 for i in items if i.status == DownloadStatus.FAILED),
            "paused": sum(1 for i in items if i.status == DownloadStatus.PAUSED),
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _schedule(self):
        """Start eligible queued items up to max_concurrent."""
        with self._lock:
            active = sum(
                1 for i in self._items.values()
                if i.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PROCESSING, DownloadStatus.PREPARING)
            )
            slots = self._max_concurrent - active
            queued = [
                i for i in self._items.values()
                if i.status == DownloadStatus.QUEUED
            ][:slots]

        for item in queued:
            self._start_item(item.id)

    def _start_item(self, item_id: int):
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.status != DownloadStatus.QUEUED:
                return
            item.status = DownloadStatus.PREPARING

        engine = DownloadEngine(item_id, item.options, self._on_engine_event)
        with self._lock:
            self._engines[item_id] = engine
        engine.start()

    def _on_engine_event(self, event_data: Dict[str, Any]):
        item_id = event_data["item_id"]
        event = event_data["event"]

        with self._lock:
            item = self._items.get(item_id)

        if item is None:
            return

        with self._lock:
            if event == "preparing":
                item.status = DownloadStatus.PREPARING

            elif event == "progress":
                item.status = DownloadStatus.DOWNLOADING
                item.progress = event_data.get("progress", item.progress)
                item.downloaded_bytes = event_data.get("downloaded_bytes", 0)
                item.total_bytes = event_data.get("total_bytes")
                item.speed = event_data.get("speed")
                item.eta = event_data.get("eta")
                filename = event_data.get("filename", "")
                if filename:
                    item.filename = filename

            elif event == "processing":
                item.status = DownloadStatus.PROCESSING
                item.progress = 99.0
                filename = event_data.get("filename", "")
                if filename:
                    item.filename = filename

            elif event == "completed":
                item.status = DownloadStatus.COMPLETED
                item.progress = 100.0
                item.completed_at = datetime.now()
                item.speed = None
                item.eta = None
                filename = event_data.get("filename", "")
                if filename:
                    item.filename = filename
                self._engines.pop(item_id, None)

            elif event == "failed":
                item.status = DownloadStatus.FAILED
                item.error_msg = event_data.get("error", "Unknown error")
                self._engines.pop(item_id, None)

            elif event == "cancelled":
                item.status = DownloadStatus.CANCELLED
                self._engines.pop(item_id, None)

        self._on_event(event_data)
        # After any terminal event, try scheduling more
        if event in ("completed", "failed", "cancelled"):
            self._schedule()

    def _emit_item_event(self, item_id: int, event: str):
        self._on_event({"item_id": item_id, "event": event})
