"""The main desktop window and its application pages."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ytdaily.config import Config, SUPPORTED_RESOLUTIONS
from ytdaily.core.downloader import Downloader
from ytdaily.core.scanner import Scanner
from ytdaily.core.state import StateManager
from ytdaily.gui.themes import THEMES, Theme, build_stylesheet, rgba
from ytdaily.gui.workers import (
    AutoDownloadWorker,
    DownloadWorker,
    PlaylistDownloadWorker,
    PlaylistFetchWorker,
    VideoPreviewWorker,
)
from ytdaily.utils.browser import SUPPORTED_BROWSERS, detect_browser
from ytdaily.utils.logging import setup_logging
from ytdaily.utils.system import get_disk_space_info

NAV_ITEMS = [
    "⌂  Dashboard",
    "◎  Channels",
    "≡  Playlists",
    "↓  Downloads",
    "↻  History",
    "⚙  Settings",
]
PAGE_DASHBOARD, PAGE_CHANNELS, PAGE_PLAYLISTS, PAGE_DOWNLOADS, PAGE_HISTORY, PAGE_SETTINGS = range(6)


def button(label: str, callback: Callable[[], None], role: str = "") -> QPushButton:
    control = QPushButton(label)
    if role:
        control.setObjectName(role)
    control.clicked.connect(callback)
    return control


ICON_PATH = Path(__file__).parent / "icon.png"


def alert(parent: QWidget, icon: QMessageBox.Icon, title: str, text: str) -> None:
    box = QMessageBox(icon, title, text, QMessageBox.StandardButton.Ok, parent)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    for button_widget in box.buttons():
        button_widget.setText(button_widget.text().replace("&", ""))
    box.exec()


def ask(parent: QWidget, icon: QMessageBox.Icon, title: str, text: str) -> bool:
    box = QMessageBox(
        icon,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        parent,
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    for button_widget in box.buttons():
        button_widget.setText(button_widget.text().replace("&", ""))
    return box.exec() == QMessageBox.StandardButton.Yes


def page_header(parent: QWidget, title: str, subtitle: str) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(32, 28, 32, 24)
    layout.setSpacing(12)
    heading = QLabel(title)
    heading.setObjectName("title")
    layout.addWidget(heading)
    sub = QLabel(subtitle)
    sub.setObjectName("subtitle")
    layout.addWidget(sub)
    return layout


class DashboardPage(QWidget):
    run_requested = Signal()

    def __init__(self, config: Config, state: StateManager) -> None:
        super().__init__()
        self.config, self.state = config, state
        self._actions: Dict[QFrame, str] = {}
        layout = page_header(self, "Dashboard", "Automatic channel and playlist downloads")

        stats = QGridLayout()
        stats.setSpacing(14)
        self.channel_card = self._card("Tracked channels")
        self.playlist_card = self._card("Tracked playlists")
        self.history_card = self._card("Downloads tracked")
        self.disk_card = self._card("Free storage")
        for index, card in enumerate((self.channel_card, self.playlist_card, self.history_card, self.disk_card)):
            stats.addWidget(card, 0, index)
        layout.addLayout(stats)

        action = QFrame()
        action.setObjectName("card")
        action_layout = QVBoxLayout(action)
        action_layout.setContentsMargins(20, 18, 20, 16)
        action_layout.setSpacing(10)
        action_title = QLabel("Automatic downloads")
        action_title.setObjectName("sectionTitle")
        action_layout.addWidget(action_title)
        action_layout.addWidget(QLabel("Scan every tracked channel and playlist, then download what is new."))
        actions = QHBoxLayout()
        self.run_button = button("Scan and download now", self.run_requested.emit)
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        actions.addWidget(self.run_button)
        actions.addStretch()
        self.run_status = QLabel("Ready.")
        self.run_status.setObjectName("hint")
        actions.addWidget(self.run_status)
        action_layout.addLayout(actions)
        self.last_download = QLabel("No completed downloads recorded yet.")
        self.last_download.setObjectName("hint")
        self.last_download.setWordWrap(True)
        action_layout.addWidget(self.last_download)
        layout.addWidget(action)

        layout.addStretch()
        self.refresh()

    def _card(self, label: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        frame.setMinimumHeight(96)
        view = QVBoxLayout(frame)
        view.setContentsMargins(18, 14, 18, 14)
        view.setSpacing(3)
        heading = QLabel(label)
        heading.setObjectName("cardLabel")
        heading.setWordWrap(True)
        value = QLabel("—")
        value.setObjectName("cardValue")
        view.addWidget(heading)
        view.addWidget(value)
        return frame

    @staticmethod
    def _set_card(card: QFrame, value: str) -> None:
        card.findChildren(QLabel)[1].setText(value)

    def refresh(self) -> None:
        self._set_card(self.channel_card, str(len(self.state.channels)))
        self._set_card(self.playlist_card, str(len(self.state.playlists)))
        total = sum(
            len(source.get("downloaded_videos", []))
            for source in self.state.channel_history.get("channels", {}).values()
        )
        self._set_card(self.history_card, str(total))
        self._set_card(self.disk_card, str(get_disk_space_info(self.config.base_video_dir).get("free_gb", "—")))
        last = self.state.get_last_download()
        if last:
            self.last_download.setText(
                f"Last download: {last.get('title', 'Unknown')} — {last.get('source', 'Unknown')}"
            )
        else:
            self.last_download.setText("No completed downloads recorded yet.")


class SourcesPage(QWidget):
    changed = Signal()
    open_in_downloads = Signal(str)

    def __init__(self, state: StateManager, kind: str) -> None:
        super().__init__()
        self.state, self.kind = state, kind
        self.items: Dict[str, str] = state.channels if kind == "channel" else state.playlists
        self.name = "Channels" if kind == "channel" else "Playlists"
        self._columns = page_header(self, self.name, f"Manage the {kind}s automatic downloads watch.")
        self.count_label = QLabel()
        self.count_label.setObjectName("hint")
        self._columns.addWidget(self.count_label)

        grid = QGridLayout()
        grid.setSpacing(14)

        add_box = QGroupBox(f"Add {kind}")
        self.identifier = QLineEdit()
        self.identifier.setPlaceholderText(
            "@handle or creator URL" if kind == "channel" else "https://... playlist or collection URL"
        )
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("Display name")
        form = QFormLayout(add_box)
        form.addRow("Identifier", self.identifier)
        form.addRow("Display name", self.display_name)
        add_button = button(f"Add {kind}", self.add)
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        form.addRow(add_button)

        table_box = QGroupBox(f"Tracked {kind}s")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Identifier"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)
        table_actions = QHBoxLayout()
        table_actions.addWidget(button(f"Remove selected {kind}", self.remove, "danger"))
        table_actions.addStretch()
        if kind == "playlist":
            table_actions.addWidget(button("Download this playlist…", self.request_download, "secondary"))
        table_layout.addLayout(table_actions)

        grid.addWidget(add_box, 0, 0)
        grid.addWidget(table_box, 1, 0)
        grid.setRowStretch(1, 1)
        self._columns.addLayout(grid, stretch=1)
        self.refresh()

    def request_download(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            source_id = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            self.open_in_downloads.emit(source_id)

    def add(self) -> None:
        source_id = self.identifier.text().strip()
        label = self.display_name.text().strip()
        if self.kind == "channel":
            if not source_id.startswith("http"):
                source_id = source_id.lstrip("@")
        if not source_id:
            alert(self, QMessageBox.Icon.Warning, f"Add {self.kind}", "Enter the playlist URL." if self.kind == "playlist" else "Enter the channel handle or URL.")
            return
        if not label:
            alert(self, QMessageBox.Icon.Warning, f"Add {self.kind}", "Enter a display name to list this source.")
            return
        if source_id in self.items:
            alert(self, QMessageBox.Icon.Warning, f"Add {self.kind}", f"You already track {label}.")
            return
        self.items[source_id] = label
        self.state.save_config()
        self.identifier.clear()
        self.display_name.clear()
        self.refresh()
        self.changed.emit()

    def remove(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        source_id = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if not ask(self, QMessageBox.Icon.Question, f"Remove {self.kind}", f"Stop tracking {self.items[source_id]}?"):
            return
        del self.items[source_id]
        self.state.save_config()
        self.refresh()
        self.changed.emit()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        for row, (source_id, label) in enumerate(sorted(self.items.items(), key=lambda item: item[1].lower())):
            self.table.insertRow(row)
            name_item = QTableWidgetItem(label)
            name_item.setToolTip(label)
            self.table.setItem(row, 0, name_item)
            identifier = QTableWidgetItem(source_id)
            identifier.setToolTip(source_id)
            identifier.setData(Qt.ItemDataRole.UserRole, source_id)
            self.table.setItem(row, 1, identifier)
        self.count_label.setText(f"{len(self.items)} tracked {self.kind}{'s' if len(self.items) != 1 else ''}")


class SingleDownloadPanel(QWidget):
    start_requested = Signal(str, bool)
    preview_requested = Signal(str)
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form_box = QGroupBox("Download a video or audio track")
        form = QFormLayout(form_box)
        self.url = QLineEdit()
        self.url.setPlaceholderText("Paste a media URL (YouTube, TikTok, Twitter/X, Instagram, Facebook, etc.)")
        self.url.returnPressed.connect(self._preview)
        self.kind = QComboBox()
        self.kind.addItems(["Video (MP4)", "Audio (MP3, 320 kbps)"])
        self.start = button("Start download", self._start)
        self.start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_button = button("Preview", self._preview, "secondary")
        self.preview_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel = button("Cancel", self.cancel_requested.emit, "danger")
        self.cancel.setEnabled(False)
        actions = QHBoxLayout()
        actions.addWidget(self.start)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.cancel)
        actions.addStretch()
        form.addRow("URL", self.url)
        form.addRow("Format", self.kind)
        form.addRow(actions)
        layout.addWidget(form_box)

        # Media preview card
        self.preview_box = QGroupBox("Media Preview")
        self.preview_box.setVisible(False)
        preview_layout = QHBoxLayout(self.preview_box)
        preview_layout.setContentsMargins(14, 12, 14, 12)
        preview_layout.setSpacing(16)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(200, 112)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background: rgba(0, 0, 0, 0.25); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);")
        preview_layout.addWidget(self.thumbnail_label)

        preview_meta = QVBoxLayout()
        preview_meta.setSpacing(4)
        self.preview_title = QLabel("Title: —")
        self.preview_title.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.preview_title.setWordWrap(True)
        self.preview_uploader = QLabel("Channel: —")
        self.preview_uploader.setObjectName("hint")
        self.preview_duration = QLabel("Duration: —")
        self.preview_duration.setObjectName("hint")
        self.preview_url_label = QLabel("")
        self.preview_url_label.setObjectName("hint")
        self.preview_url_label.setWordWrap(True)

        preview_meta.addWidget(self.preview_title)
        preview_meta.addWidget(self.preview_uploader)
        preview_meta.addWidget(self.preview_duration)
        preview_meta.addWidget(self.preview_url_label)
        preview_meta.addStretch()
        preview_layout.addLayout(preview_meta, stretch=1)

        layout.addWidget(self.preview_box)

        self.status = QLabel("Ready.")
        self.status.setObjectName("hint")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        progress_row = QVBoxLayout()
        progress_row.addWidget(self.progress)
        progress_row.addWidget(self.status)
        layout.addLayout(progress_row)

        self.log = QTextEdit()
        self.log.setObjectName("terminal")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Download progress will appear here.")
        layout.addWidget(self.log, stretch=1)

    def _preview(self) -> None:
        url = self.url.text().strip()
        if not url:
            alert(self, QMessageBox.Icon.Warning, "URL required", "Paste a video URL first.")
            return
        self.preview_button.setEnabled(False)
        self.status.setText("Fetching media preview…")
        self.preview_requested.emit(url)

    def display_preview(self, data: dict) -> None:
        self.preview_button.setEnabled(True)
        self.preview_box.setVisible(True)
        title = data.get("title", "Unknown title")
        uploader = data.get("uploader", "Unknown")
        duration = data.get("duration", "Unknown")
        if isinstance(duration, (int, float)):
            from ytdaily.utils.cache import format_duration
            duration = format_duration(int(duration))
        url_text = data.get("url") or self.url.text().strip()

        self.preview_title.setText(title)
        self.preview_uploader.setText(f"👤 {uploader}")
        self.preview_duration.setText(f"⏱️ Duration: {duration}")
        self.preview_url_label.setText(f"🔗 {url_text}")

        thumb_bytes = data.get("thumbnail_bytes")
        if thumb_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(thumb_bytes):
                self.thumbnail_label.setPixmap(
                    pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.thumbnail_label.setText("No Preview")
        else:
            self.thumbnail_label.setText("No Preview")

    def _start(self) -> None:
        url = self.url.text().strip()
        if not url:
            alert(self, QMessageBox.Icon.Warning, "URL required", "Paste a video URL first.")
            return
        self.log.clear()
        self.progress.setValue(0)
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.status.setText("Starting download…")
        self.start_requested.emit(url, self.kind.currentIndex() == 1)

    def handle_progress(self, data: dict) -> None:
        event_type = data.get("type", "update")
        if event_type == "preview":
            self.display_preview(data)
            return
        elif event_type == "download":
            percent = float(data.get("percent", 0))
            self.progress.setValue(round(percent))
            self.status.setText(f"Downloading… {percent:.1f}%  ·  {data.get('speed', '')}  ·  ETA {data.get('eta', '')}")
        elif event_type in ("extract", "converting"):
            self.status.setText("Processing media…")
        elif event_type == "starting":
            self.status.setText(f"Preparing: {data.get('title', '')}")
        elif event_type == "failed":
            self.log.append(f"❌ {data.get('message', 'Download failed')}")
            return
        elif event_type == "completed":
            self.log.append(f"✔ Saved: {data.get('title', '')}")
            return
        else:
            return

    def complete(self, success: bool, message: str) -> None:
        self.start.setEnabled(True)
        self.cancel.setEnabled(False)
        self.status.setText(message)
        if success:
            self.progress.setValue(100)


class PlaylistPanel(QWidget):
    fetch_requested = Signal(str)
    download_requested = Signal(str, str, object)
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._entries: List[Dict[str, object]] = []
        self._busy = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form_box = QGroupBox("Download a playlist")
        form_layout = QVBoxLayout(form_box)
        form_layout.setSpacing(10)
        url_row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://... playlist or collection URL")
        self.fetch_button = button("Fetch videos", self._fetch)
        self.fetch_button.setEnabled(True)
        url_row.addWidget(self.url, stretch=1)
        url_row.addWidget(self.fetch_button)
        form_layout.addLayout(url_row)
        self.info = QLabel()
        self.info.setObjectName("hint")
        self.info.setWordWrap(True)
        form_layout.addWidget(self.info)

        controls = QHBoxLayout()
        self.select_all = button("Select all", self._select_all, "secondary")
        self.clear_selection = button("Clear selection", self._clear_selection, "secondary")
        controls.addWidget(self.select_all)
        controls.addWidget(self.clear_selection)
        controls.addStretch()
        self.kind = QComboBox()
        self.kind.addItems(["Video (MP4)", "Audio (MP3, 320 kbps)"])
        controls.addWidget(self.kind)
        self.download_button = button("Download selected", self._download)
        self.download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        controls.addWidget(self.download_button)
        self.cancel = button("Cancel", self.cancel_requested.emit, "danger")
        self.cancel.setEnabled(False)
        controls.addWidget(self.cancel)
        form_layout.addLayout(controls)
        layout.addWidget(form_box)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["#", "Title"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_download_button)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.table, stretch=1)

        self.overall = QProgressBar()
        self.current = QProgressBar()
        overall_row = QHBoxLayout()
        overall_label = QLabel("Overall")
        overall_label.setObjectName("hint")
        overall_row.addWidget(overall_label)
        overall_row.addWidget(self.overall, stretch=1)
        current_row = QHBoxLayout()
        current_label = QLabel("Item")
        current_label.setObjectName("hint")
        current_row.addWidget(current_label)
        current_row.addWidget(self.current, stretch=1)
        self.status = QLabel("Paste a playlist or collection URL and fetch its videos to pick what to download.")
        self.status.setObjectName("hint")
        layout.addLayout(overall_row)
        layout.addLayout(current_row)
        layout.addWidget(self.status)
        self._set_enabled(False)

    def _fetch(self) -> None:
        url = self.url.text().strip()
        if not url:
            alert(self, QMessageBox.Icon.Warning, "URL required", "Paste a playlist or collection URL first.")
            return
        self.fetch_requested.emit(url)

    def _download(self) -> None:
        items = self.selected_indices()
        if not items:
            return
        download_type = "audio" if self.kind.currentIndex() == 1 else "video"
        self.download_requested.emit(self.url.text().strip(), download_type, items)

    def _select_all(self) -> None:
        self.table.selectAll()

    def _clear_selection(self) -> None:
        self.table.clearSelection()

    def selected_indices(self) -> List[int]:
        return sorted(
            int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).isSelected()
        )

    def _update_download_button(self) -> None:
        count = len(self.selected_indices())
        self.download_button.setText(f"Download selected ({count})" if count else "Download selected")
        if not self._busy:
            self.download_button.setEnabled(count > 0)

    def _set_enabled(self, enabled: bool) -> None:
        self.select_all.setEnabled(enabled)
        self.clear_selection.setEnabled(enabled)
        self.kind.setEnabled(enabled)
        self._update_download_button()

    def set_fetching(self) -> None:
        self._busy = True
        self.url.setEnabled(False)
        self.fetch_button.setEnabled(False)
        self.info.clear()
        self.table.setRowCount(0)
        self._set_enabled(False)
        self.status.setText("Fetching playlist details…")

    def display_playlist(self, payload: dict) -> None:
        info = payload.get("info", {})
        videos = payload.get("videos", [])
        self._entries = videos
        title = info.get("title", "Unknown playlist")
        uploader = info.get("uploader", "Unknown")
        self.info.setText(f"“{title}” · {uploader} · {len(videos)} videos")
        self.table.setRowCount(0)
        for row, entry in enumerate(videos):
            index = int(entry.get("playlist_index", row + 1) or row + 1)
            self.table.insertRow(row)
            index_item = QTableWidgetItem(str(index))
            index_item.setData(Qt.ItemDataRole.UserRole, index)
            self.table.setItem(row, 0, index_item)
            title_item = QTableWidgetItem(entry.get("title", "Untitled"))
            title_item.setToolTip(str(entry.get("title", "Untitled")))
            self.table.setItem(row, 1, title_item)
        self.table.setCurrentCell(0, 0)
        self.table.clearSelection()
        self.overall.setValue(0)
        self.current.setValue(0)
        self._busy = False
        self.url.setEnabled(True)
        self.fetch_button.setEnabled(True)
        self._set_enabled(bool(videos))
        self.status.setText(f"Ready: {self.table.rowCount()} videos listed. Select what to download.")

    def set_downloading(self) -> None:
        self._busy = True
        self.url.setEnabled(False)
        self.fetch_button.setEnabled(False)
        self._set_enabled(False)
        self.cancel.setEnabled(True)
        self.overall.setValue(0)
        self.current.setValue(0)
        self.status.setText("Preparing playlist download…")

    def handle_progress(self, data: dict) -> None:
        event_type = data.get("type")
        if event_type == "playlist_progress":
            self.overall.setValue(0)
            self.current.setValue(0)
            self.status.setText(f"Video {data.get('current', '?')} of {data.get('total', '?')}…")
        elif event_type == "playlist_current":
            self.current.setValue(round(float(data.get("percent", 0))))
            self.overall.setValue(round(float(data.get("overall", 0))))
            self.status.setText(
                f"Video {data.get('item', '?')}/{data.get('total', '?')}  ·  {data.get('speed', '')}  ·  ETA {data.get('eta', '')}"
            )
        elif event_type == "completed":
            self.overall.setValue(100)
            self.current.setValue(100)
        elif event_type == "failed":
            self.status.setText(f"…{data.get('message', 'error')}")

    def fetch_finished(self, success: bool, message: str) -> None:
        self.fetch_button.setEnabled(True)
        self.url.setEnabled(True)
        if not success:
            self._busy = False
            self._set_enabled(False)
            self.status.setText(message)

    def complete(self, success: bool, message: str) -> None:
        self._busy = False
        self.cancel.setEnabled(False)
        self.fetch_button.setEnabled(True)
        self.url.setEnabled(True)
        self._set_enabled(bool(self._entries))
        self.status.setText(message)
        if success:
            self.overall.setValue(100)


class HistoryPage(QWidget):
    changed = Signal()

    def __init__(self, state: StateManager) -> None:
        super().__init__()
        self.state = state
        layout = page_header(self, "History", "Everything automatic and manual downloads have saved")
        self.count_label = QLabel()
        self.count_label.setObjectName("hint")
        layout.addWidget(self.count_label)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, source, or video ID")
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Title", "Source", "Saved"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        items = self.state.get_all_downloaded_videos(self.search.text().strip() or None, limit=500)
        self.table.setRowCount(0)
        for row, item in enumerate(items):
            self.table.insertRow(row)
            title_item = QTableWidgetItem(item["title"])
            title_item.setToolTip(item["title"])
            self.table.setItem(row, 0, title_item)
            source_item = QTableWidgetItem(item["source"])
            source_item.setToolTip(item["source"])
            self.table.setItem(row, 1, source_item)
            self.table.setItem(row, 2, QTableWidgetItem(item["downloaded_at"][:19].replace("T", " ")))
        count = len(items)
        self.count_label.setText(f"{count} download{'s' if count != 1 else ''}")


class SettingsPage(QWidget):
    changed = Signal()
    theme_changed = Signal(str)

    def __init__(self, config: Config, state: StateManager, current_theme: str) -> None:
        super().__init__()
        self.config, self.state = config, state
        self._theme_buttons: Dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(12)
        heading = QLabel("Settings")
        heading.setObjectName("title")
        layout.addWidget(heading)
        sub = QLabel("Themes, folders, and download behaviour")
        sub.setObjectName("subtitle")
        layout.addWidget(sub)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(14)

        section = QLabel("Appearance")
        section.setObjectName("sectionTitle")
        content_layout.addWidget(section)
        theme_note = QLabel("Catppuccin Mocha is the default theme.")
        theme_note.setObjectName("hint")
        content_layout.addWidget(theme_note)
        cards = QGridLayout()
        cards.setSpacing(14)
        card_positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]
        for theme, (row, column) in zip(THEMES.values(), card_positions):
            cards.addWidget(self._theme_card(theme), row, column)
        content_layout.addLayout(cards)

        engine_section = QLabel("Engine")
        engine_section.setObjectName("sectionTitle")
        content_layout.addWidget(engine_section)
        content_layout.addWidget(self._engine_card())

        self.engine_preview = QTextEdit()
        self.engine_preview.setObjectName("terminal")
        self.engine_preview.setReadOnly(True)
        self.engine_preview.setFixedHeight(120)
        content_layout.addWidget(self.engine_preview)
        self.engine_preview.setPlainText(self._engine_summary())
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

    def _theme_card(self, theme: Theme) -> QPushButton:
        card = QPushButton()
        card.setObjectName("themeCard")
        card.setCheckable(True)
        card.setAutoExclusive(True)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(96)
        card.setMinimumWidth(190)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        view = QVBoxLayout(card)
        view.setContentsMargins(12, 10, 12, 12)
        view.setSpacing(8)
        name = QLabel(theme.name)
        name.setObjectName("themeCardName")
        view.addWidget(name)
        swatches = QHBoxLayout()
        swatches.setSpacing(6)
        for color in theme.swatches:
            swatch = QLabel()
            swatch.setFixedSize(20, 20)
            swatch.setStyleSheet(
                f"background: {color}; border-radius: 10px; border: 1px solid {theme.border_subtle};"
            )
            swatches.addWidget(swatch)
        swatches.addStretch()
        view.addLayout(swatches)
        card.clicked.connect(lambda _checked=False, key=theme.key: self.theme_changed.emit(key))
        self._theme_buttons[theme.key] = card
        return card

    def sync_theme(self, theme_key: str) -> None:
        for key, card in self._theme_buttons.items():
            selected = key == theme_key
            card.setChecked(selected)
            if card.property("selected") != selected:
                card.setProperty("selected", selected)
                card.style().unpolish(card)
                card.style().polish(card)

    def _engine_card(self) -> QGroupBox:
        box = QGroupBox("Download settings")
        form = QFormLayout(box)
        self.video_dir = self._path_field(form, "Video folder", self.config.base_video_dir)
        self.audio_dir = self._path_field(form, "Audio folder", self.config.base_audio_dir)
        self.playlist_dir = self._path_field(form, "Playlist folder", self.config.base_playlist_dir)
        self.podcast_dir = self._path_field(form, "Podcast folder", self.config.base_podcast_dir)
        self.resolution = QComboBox()
        self.resolution.addItems(SUPPORTED_RESOLUTIONS)
        self.resolution.setCurrentText(self.config.max_resolution)
        self.browser = QComboBox()
        self.browser.addItems(["auto", "none", *SUPPORTED_BROWSERS])
        self.browser.setCurrentText(self.config.browser)
        self.parallel = QSpinBox()
        self.parallel.setRange(1, 10)
        self.parallel.setValue(self.config.max_parallel_downloads)
        self.cleanup = QSpinBox()
        self.cleanup.setRange(1, 3650)
        self.cleanup.setValue(self.config.cleanup_days)
        self.filter_shorts = QCheckBox("Skip videos shorter than one minute")
        self.filter_shorts.setChecked(self.config.filter_shorts)
        form.addRow("Maximum resolution", self.resolution)
        form.addRow("Cookie browser", self.browser)
        form.addRow("Parallel downloads", self.parallel)
        form.addRow("Retention days", self.cleanup)
        form.addRow("Shorts filter", self.filter_shorts)
        form.addRow(button("Save settings", self.save))
        return box

    def _engine_summary(self) -> str:
        return (
            f"engine    bestvideo[height<={self.resolution.currentText()}]+bestaudio/best"
            f" -> {self.config.output_format}\n"
            f"parallel  {self.parallel.value()} concurrent jobs"
            f"   ·   shorts {'skipped' if self.filter_shorts.isChecked() else 'kept'}"
            f"   ·   {self.cleanup.value()}-day retention\n"
            f"video out {self.video_dir.text()}\n"
            f"audio out {self.audio_dir.text()}"
        )

    def _path_field(self, form: QFormLayout, label: str, value) -> QLineEdit:
        """Return a QLineEdit wired to a folder picker row inside ``form``."""
        line = QLineEdit(str(value))
        browse = button("Browse…", lambda: self._choose_folder(line), "secondary")
        row = QHBoxLayout()
        row.addWidget(line)
        row.addWidget(browse)
        form.addRow(label, row)
        return line

    def _choose_folder(self, field: QLineEdit) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose download folder", field.text())
        if selected:
            field.setText(selected)

    def save(self) -> None:
        try:
            self.config.base_video_dir = Path(self.video_dir.text()).expanduser()
            self.config.base_audio_dir = Path(self.audio_dir.text()).expanduser()
            self.config.base_playlist_dir = Path(self.playlist_dir.text()).expanduser()
            self.config.base_podcast_dir = Path(self.podcast_dir.text()).expanduser()
            self.config.max_resolution = self.resolution.currentText()
            self.config.browser = self.browser.currentText()
            self.config.max_parallel_downloads = self.parallel.value()
            self.config.cleanup_days = self.cleanup.value()
            self.config.filter_shorts = self.filter_shorts.isChecked()
            self.config.ensure_directories()
            self.config.validate()
            self.state.save_config()
        except OSError as error:
            alert(self, QMessageBox.Icon.Critical, "Could not save settings", str(error))
            return
        self.engine_preview.setPlainText(self._engine_summary())
        alert(self, QMessageBox.Icon.Information, "Settings saved", "Your settings have been saved.")
        self.changed.emit()


class DownloadPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tabs = QTabWidget()
        self.single = SingleDownloadPanel()
        self.playlist = PlaylistPanel()
        self.tabs.addTab(self.single, "Single video")
        self.tabs.addTab(self.playlist, "Playlist")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tabs)


class MainWindow(QMainWindow):
    """Desktop application shell shared by Windows, Linux, and macOS."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.logger = setup_logging(config.app_log_path, config.max_log_size, config.max_log_files)
        self.state = StateManager(config, self.logger)
        self.scanner = Scanner(config, self.state, self.logger)
        self.downloader = Downloader(config, self.state, self.scanner, self.logger)
        self._jobs: Dict[str, tuple] = {}

        self.setWindowTitle("Ytdaily")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setMinimumSize(980, 650)
        self.resize(1180, 760)
        self.theme_key = QSettings("Ytdaily", "GUI").value("theme", "catppuccin-mocha", type=str)
        if self.theme_key not in THEMES:
            self.theme_key = "catppuccin-mocha"
        self._build_ui()
        self._build_tray()
        self.apply_theme(self.theme_key)

    def apply_theme(self, theme_key: str) -> None:
        if theme_key not in THEMES:
            theme_key = "catppuccin-mocha"
        self.theme_key = theme_key
        theme = THEMES[theme_key]
        self.setStyleSheet(build_stylesheet(theme_key))
        self.logo.setStyleSheet(
            f"background: {rgba(theme.accent, 15)}; color: {theme.accent};"
            " border-radius: 12px; font-weight: 700; font-size: 16px;"
        )
        self.settings.sync_theme(theme_key)
        QSettings("Ytdaily", "GUI").setValue("theme", theme_key)

    def _build_ui(self) -> None:
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        central = QWidget()
        central.setLayout(root)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        rail = QVBoxLayout(self.sidebar)
        rail.setContentsMargins(18, 22, 18, 18)
        rail.setSpacing(20)
        brand = QHBoxLayout()
        self.logo = QLabel("▶")
        self.logo.setObjectName("logo")
        self.logo.setFixedSize(38, 38)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.addWidget(self.logo)
        brand.addSpacing(8)
        brand_title = QLabel("Ytdaily")
        brand_title.setObjectName("brandTitle")
        brand.addWidget(brand_title)
        brand.addStretch()
        rail.addLayout(brand)
        self.navigation = QListWidget()
        self.navigation.setObjectName("nav")
        self.navigation.addItems(NAV_ITEMS)
        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rail.addWidget(self.navigation, stretch=1)
        footer = QLabel(f"Cookie browser: {detect_browser()}")
        footer.setObjectName("sidebarFooter")
        footer.setWordWrap(True)
        rail.addWidget(footer)

        self.pages = QStackedWidget()
        self.pages.setObjectName("workspace")
        self.dashboard = DashboardPage(self.config, self.state)
        self.channels = SourcesPage(self.state, "channel")
        self.playlists = SourcesPage(self.state, "playlist")
        self.download = DownloadPage()
        self.history = HistoryPage(self.state)
        self.settings = SettingsPage(self.config, self.state, self.theme_key)
        for page in (self.dashboard, self.channels, self.playlists, self.download, self.history, self.settings):
            self.pages.addWidget(page)
        root.addWidget(self.sidebar)
        root.addWidget(self.pages, stretch=1)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.navigation.currentRowChanged.connect(self.change_page)
        self.navigation.setCurrentRow(0)

        self.dashboard.run_requested.connect(self.start_auto_download)
        self.settings.theme_changed.connect(self.apply_theme)
        self.download.single.start_requested.connect(self.start_download)
        self.download.single.preview_requested.connect(self.start_preview_fetch)
        self.download.single.cancel_requested.connect(self.cancel_single_download)
        self.download.playlist.fetch_requested.connect(self.start_playlist_fetch)
        self.download.playlist.download_requested.connect(self.start_playlist_download)
        self.download.playlist.cancel_requested.connect(self.cancel_playlist_download)
        self.playlists.open_in_downloads.connect(self.open_playlist_in_downloads)
        for page in (self.channels, self.playlists, self.settings):
            page.changed.connect(self.refresh_all)

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.windowIcon())
        self.tray.setToolTip("Ytdaily")
        show_action = QAction("Show Ytdaily", self)
        show_action.triggered.connect(self.showNormal)
        run_action = QAction("Scan and download", self)
        run_action.triggered.connect(self.start_auto_download)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu = self.tray.contextMenu() or QMenu(self)
        menu.addAction(show_action)
        menu.addAction(run_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda _: self.showNormal())
        self.tray.show()

    def change_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == PAGE_DASHBOARD:
            self.dashboard.refresh()
        elif index == PAGE_HISTORY:
            self.history.refresh()

    def refresh_all(self) -> None:
        self.dashboard.refresh()
        self.channels.refresh()
        self.playlists.refresh()
        self.history.refresh()

    def _start_job(self, slot: str, worker: object, done: Callable[..., None]) -> bool:
        if slot in self._jobs:
            return False
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda key=slot: self._jobs.pop(key, None))
        self._jobs[slot] = (worker, thread)
        thread.start()
        return True

    def _job_running(self, slot: str) -> bool:
        return slot in self._jobs

    def start_download(self, url: str, is_audio: bool) -> None:
        worker = DownloadWorker(self.downloader, self.scanner, url, is_audio)
        worker.progress.connect(self.download.single.handle_progress)
        if not self._start_job("single", worker, self._download_finished):
            alert(self, QMessageBox.Icon.Information, "Job already running", "Wait for the active job to finish or cancel it first.")
            self.download.single.start.setEnabled(True)
            self.download.single.cancel.setEnabled(False)
            return
        self.statusBar().showMessage("Download started…")

    def _download_finished(self, success: bool, message: str) -> None:
        self.download.single.complete(success, message)
        self.statusBar().showMessage(message, 5000)
        self.refresh_all()
        if self.tray is not None:
            self.tray.showMessage("Ytdaily", message)

    def start_preview_fetch(self, url: str) -> None:
        if self._job_running("preview"):
            return
        worker = VideoPreviewWorker(self.scanner, url)
        worker.fetched.connect(self.download.single.display_preview)
        if not self._start_job("preview", worker, self._preview_finished):
            self.download.single.preview_button.setEnabled(True)
            self.download.single.status.setText("A preview job is already running.")

    def _preview_finished(self, success: bool, message: str) -> None:
        self.download.single.preview_button.setEnabled(True)
        self.download.single.status.setText(message)
        self.statusBar().showMessage(message, 5000)

    def start_auto_download(self) -> None:
        if self._job_running("auto"):
            return
        self.dashboard.run_button.setEnabled(False)
        worker = AutoDownloadWorker(self.config, self.state, self.scanner, self.downloader)
        worker.status.connect(self._auto_status)
        worker.progress.connect(self.download.single.handle_progress)
        if not self._start_job("auto", worker, self._auto_finished):
            self.dashboard.run_button.setEnabled(True)
            self._auto_status("A job is already running. Cancel it or wait for it to finish.")

    def _auto_status(self, text: str) -> None:
        self.dashboard.run_status.setText(text)
        self.statusBar().showMessage(text)

    def _auto_finished(self, count: int, message: str) -> None:
        self.dashboard.run_button.setEnabled(True)
        self.dashboard.run_status.setText(message)
        self.statusBar().showMessage(message, 5000)
        self.refresh_all()
        if self.tray is not None:
            self.tray.showMessage("Ytdaily", message)

    def start_playlist_fetch(self, url: str) -> None:
        if self._job_running("playlist"):
            alert(self, QMessageBox.Icon.Information, "Busy", "A playlist job is already running. Cancel it first or wait for it.")
            return
        self.download.playlist.set_fetching()
        worker = PlaylistFetchWorker(self.scanner, url)
        worker.fetched.connect(self.download.playlist.display_playlist)
        if not self._start_job("playlist", worker, self._playlist_fetch_done):
            self.download.playlist.fetch_finished(False, "A playlist download is still running.")

    def _playlist_fetch_done(self, success: bool, message: str) -> None:
        self.download.playlist.fetch_finished(success, message)
        self.statusBar().showMessage(message, 5000)

    def start_playlist_download(self, url: str, download_type: str, items: object) -> None:
        if self._job_running("playlist"):
            alert(self, QMessageBox.Icon.Information, "Busy", "A playlist job is already running. Cancel it first or wait for it.")
            return
        item_list = sorted(set(int(index) for index in items)) if items else None
        self.download.playlist.set_downloading()
        worker = PlaylistDownloadWorker(self.downloader, url, download_type, item_list or [])
        worker.progress.connect(self.download.playlist.handle_progress)
        if not self._start_job("playlist", worker, self._playlist_download_done):
            self.download.playlist.complete(False, "Could not start download.")

    def _playlist_download_done(self, success: bool, message: str) -> None:
        self.download.playlist.complete(success, message)
        self.statusBar().showMessage(message, 5000)
        self.refresh_all()
        if self.tray is not None:
            self.tray.showMessage("Ytdaily", message)

    def open_playlist_in_downloads(self, url: str) -> None:
        self.navigation.setCurrentRow(PAGE_DOWNLOADS)
        self.download.tabs.setCurrentIndex(1)
        self.download.playlist.url.setText(url)
        if not url:
            return
        self.start_playlist_fetch(url)

    def cancel_single_download(self) -> None:
        job = self._jobs.get("single")
        if job:
            job[0].cancel()
            self.statusBar().showMessage("Cancelling current download…")

    def cancel_playlist_download(self) -> None:
        job = self._jobs.get("playlist")
        if job:
            job[0].cancel()
            self.download.playlist.status.setText("Cancelling…")
            self.statusBar().showMessage("Cancelling playlist download…")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.tray is not None and self.tray.isVisible():
            self.hide()
            self.tray.showMessage("Ytdaily", "Ytdaily is still running in the system tray.")
            event.ignore()
            return
        if self.logger:
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
        event.accept()
