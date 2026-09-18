"""Qt workers that keep yt-dlp and filesystem work off the GUI thread."""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Tuple

from PySide6.QtCore import QObject, Signal, Slot

from ytdaily.config import Config
from ytdaily.core.downloader import Downloader
from ytdaily.core.scanner import Scanner
from ytdaily.core.state import StateManager


class DownloadWorker(QObject):
    """Download one video or audio item and relay backend events to Qt."""

    progress = Signal(dict)
    finished = Signal(bool, str)

    def __init__(
        self,
        downloader: Downloader,
        scanner: Scanner,
        url: str,
        is_audio: bool,
    ) -> None:
        super().__init__()
        self.downloader = downloader
        self.scanner = scanner
        self.url = url
        self.is_audio = is_audio
        self.cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        info = self.scanner.get_video_info(self.url)
        if not info:
            self.finished.emit(False, "Could not read video details. Check the URL and connection.")
            return
        self.progress.emit({"type": "starting", "title": info["title"]})
        success, _ = self.downloader.download_video(
            info,
            info.get("uploader", "Manual download"),
            is_manual=True,
            is_audio=self.is_audio,
            progress_callback=self.progress.emit,
            cancel_event=self.cancel_event,
            show_console=False,
        )
        self.finished.emit(success, "Download complete." if success else "Download failed or was cancelled.")

    @Slot()
    def cancel(self) -> None:
        self.cancel_event.set()


class AutoDownloadWorker(QObject):
    """Scan tracked sources and download newly discovered items in the background."""

    progress = Signal(dict)
    status = Signal(str)
    finished = Signal(int, str)

    def __init__(self, config: Config, state: StateManager, scanner: Scanner, downloader: Downloader) -> None:
        super().__init__()
        self.config = config
        self.state = state
        self.scanner = scanner
        self.downloader = downloader
        self.cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        tasks: List[Tuple[Dict[str, Any], str, str, str]] = []
        first_run = self.state.is_first_run()
        limit = self.config.initial_videos_per_channel if first_run else self.config.max_videos_per_channel

        for source_id, source_name, source_type in self._sources():
            if self.cancel_event.is_set():
                self.finished.emit(0, "Scan cancelled.")
                return
            self.status.emit(f"Scanning {source_name}…")
            source_url = source_id if source_type == "playlist" or source_id.startswith("http") else f"https://www.youtube.com/@{source_id}/videos"
            for item in self.scanner.get_all_recent_videos(source_url, source_name, limit, silent=True):
                if self.state.is_video_downloaded(source_id, item["id"]):
                    continue
                if self.config.filter_shorts and item.get("duration", 0) and item["duration"] < 60:
                    continue
                tasks.append((item, source_id, source_name, source_type))

        if first_run:
            self.state.mark_first_run_completed()

        succeeded = 0
        for item, source_id, source_name, source_type in tasks:
            if self.cancel_event.is_set():
                break
            self.status.emit(f"Downloading: {item.get('title', 'Untitled')}")
            success, video_id = self.downloader.download_video(
                item,
                source_name,
                progress_callback=self.progress.emit,
                cancel_event=self.cancel_event,
                show_console=False,
            )
            if success:
                succeeded += 1
                self.state.update_channel_history(source_id, item)
                self.state.download_history["playlists" if source_type == "playlist" else "channels"][source_id] = video_id
                self.state.save_download_history()

        message = "Scan cancelled." if self.cancel_event.is_set() else f"Downloaded {succeeded} new item(s)."
        self.finished.emit(succeeded, message)

    def _sources(self) -> List[Tuple[str, str, str]]:
        channels = [(key, name, "channel") for key, name in self.state.channels.items()]
        playlists = [(key, name, "playlist") for key, name in self.state.playlists.items()]
        return channels + playlists

    @Slot()
    def cancel(self) -> None:
        self.cancel_event.set()
