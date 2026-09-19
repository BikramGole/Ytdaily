"""The main desktop window and its application pages."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
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
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ytdaily.config import Config, SUPPORTED_RESOLUTIONS
from ytdaily.core.downloader import Downloader
from ytdaily.core.scanner import Scanner
from ytdaily.core.state import StateManager
from ytdaily.gui.workers import AutoDownloadWorker, DownloadWorker
from ytdaily.utils.browser import SUPPORTED_BROWSERS, detect_browser
from ytdaily.utils.logging import setup_logging
from ytdaily.utils.system import get_disk_space_info


APP_STYLE = """
QMainWindow { background: #171923; color: #edf2f7; }
QWidget { font-family: Segoe UI, Arial, sans-serif; font-size: 13px; }
QListWidget { background: #202330; border: 0; color: #cbd5e0; padding: 8px; }
QListWidget::item { padding: 11px 14px; border-radius: 6px; }
QListWidget::item:selected { background: #4c51bf; color: white; }
QLabel#title { font-size: 24px; font-weight: 700; color: #f7fafc; }
QLabel#subtitle { color: #a0aec0; }
QFrame#card, QGroupBox { background: #242936; border: 1px solid #3a4052; border-radius: 9px; }
QGroupBox { margin-top: 12px; padding: 14px; font-weight: 600; color: #e2e8f0; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
QPushButton { background: #4c51bf; color: white; border: 0; border-radius: 6px; padding: 8px 13px; font-weight: 600; }
QPushButton:hover { background: #5a67d8; }
QPushButton:disabled { background: #4a5568; color: #a0aec0; }
QPushButton#secondary { background: #3a4052; }
QPushButton#danger { background: #c53030; }
QLineEdit, QComboBox, QSpinBox, QTextEdit, QTableWidget { background: #202330; color: #edf2f7; border: 1px solid #4a5568; border-radius: 5px; padding: 6px; }
QTableWidget { gridline-color: #3a4052; }
QHeaderView::section { background: #2d3748; color: #e2e8f0; border: 0; padding: 7px; font-weight: 600; }
QProgressBar { border: 1px solid #4a5568; border-radius: 5px; text-align: center; background: #202330; }
QProgressBar::chunk { background: #48bb78; border-radius: 4px; }
QStatusBar { background: #202330; color: #cbd5e0; }
"""


def button(label: str, callback: Callable[[], None], role: str = "") -> QPushButton:
    control = QPushButton(label)
    if role:
        control.setObjectName(role)
    control.clicked.connect(callback)
    return control


class DashboardPage(QWidget):
    run_requested = Signal()

    def __init__(self, config: Config, state: StateManager) -> None:
        super().__init__()
        self.config, self.state = config, state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Ytdaily")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Your desktop YouTube automation hub")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        cards = QGridLayout()
        self.channel_card = self._card("Tracked channels")
        self.playlist_card = self._card("Tracked playlists")
        self.history_card = self._card("Downloads tracked")
        self.disk_card = self._card("Free storage")
        for index, card in enumerate((self.channel_card, self.playlist_card, self.history_card, self.disk_card)):
            cards.addWidget(card, 0, index)
        layout.addLayout(cards)

        action_box = QGroupBox("Automatic download")
        action_layout = QVBoxLayout(action_box)
        action_layout.addWidget(QLabel("Scan all tracked channels and playlists, then download newly found items."))
        self.run_button = button("Scan and download now", self.run_requested.emit)
        action_layout.addWidget(self.run_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.run_status = QLabel("Ready.")
        self.run_status.setObjectName("subtitle")
        action_layout.addWidget(self.run_status)
        layout.addWidget(action_box)

        last = state.get_last_download()
        self.last_download = QLabel()
        self.last_download.setWordWrap(True)
        layout.addWidget(self.last_download)
        layout.addStretch()
        self.refresh()

    def _card(self, heading: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        view = QVBoxLayout(frame)
        heading_label = QLabel(heading)
        heading_label.setObjectName("subtitle")
        value = QLabel("—")
        value.setObjectName("title")
        value.setProperty("value", True)
        view.addWidget(heading_label)
        view.addWidget(value)
        return frame

    @staticmethod
    def _set_card(card: QFrame, value: str) -> None:
        card.findChildren(QLabel)[1].setText(value)

    def refresh(self) -> None:
        self._set_card(self.channel_card, str(len(self.state.channels)))
        self._set_card(self.playlist_card, str(len(self.state.playlists)))
        total = sum(len(source.get("downloaded_videos", [])) for source in self.state.channel_history.get("channels", {}).values())
        self._set_card(self.history_card, str(total))
        self._set_card(self.disk_card, get_disk_space_info(self.config.base_video_dir).get("free_gb", "Unknown"))
        last = self.state.get_last_download()
        if last:
            self.last_download.setText(f"Last download: <b>{last.get('title', 'Unknown')}</b> from {last.get('source', 'Unknown')}")
        else:
            self.last_download.setText("No completed downloads recorded yet.")


class SourcesPage(QWidget):
    changed = Signal()

    def __init__(self, state: StateManager, kind: str) -> None:
        super().__init__()
        self.state, self.kind = state, kind
        self.items: Dict[str, str] = state.channels if kind == "channel" else state.playlists
        name = "Channels" if kind == "channel" else "Playlists"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel(name)
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Manage YouTube {kind}s tracked by automatic downloads."), alignment=Qt.AlignmentFlag.AlignLeft)

        add_box = QGroupBox(f"Add {kind}")
        add_layout = QFormLayout(add_box)
        self.identifier = QLineEdit()
        self.identifier.setPlaceholderText("@channel-handle or channel URL" if kind == "channel" else "https://www.youtube.com/playlist?list=…")
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("Display name")
        add_layout.addRow("Channel handle / URL" if kind == "channel" else "Playlist URL", self.identifier)
        add_layout.addRow("Display name", self.display_name)
        add_layout.addRow(button(f"Add {kind}", self.add))
        layout.addWidget(add_box)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Channel handle / URL" if kind == "channel" else "Playlist URL"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        layout.addWidget(button(f"Remove selected {kind}", self.remove, "danger"), alignment=Qt.AlignmentFlag.AlignLeft)
        self.refresh()

    def add(self) -> None:
        source_id = self.identifier.text().strip()
        label = self.display_name.text().strip()
        if self.kind == "channel":
            source_id = source_id.lstrip("@")
        if not source_id or not label:
            QMessageBox.warning(self, "Missing information", "Enter both an identifier and a display name.")
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
        if QMessageBox.question(self, "Remove source", f"Remove {self.items[source_id]}?") != QMessageBox.StandardButton.Yes:
            return
        del self.items[source_id]
        self.state.save_config()
        self.refresh()
        self.changed.emit()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        for row, (source_id, label) in enumerate(sorted(self.items.items(), key=lambda item: item[1].lower())):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(label))
            identifier = QTableWidgetItem(source_id)
            identifier.setData(Qt.ItemDataRole.UserRole, source_id)
            self.table.setItem(row, 1, identifier)


class DownloadPage(QWidget):
    def __init__(self, start_download: Callable[[str, bool], None], cancel_download: Callable[[], None]) -> None:
        super().__init__()
        self.start_download, self.cancel_download = start_download, cancel_download
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Single download")
        title.setObjectName("title")
        layout.addWidget(title)
        box = QGroupBox("Download a video or audio track")
        form = QFormLayout(box)
        self.url = QLineEdit()
        self.url.setPlaceholderText("Paste a YouTube video URL")
        self.kind = QComboBox()
        self.kind.addItems(["Video (MP4)", "Audio (MP3, 320 kbps)"])
        self.start = button("Start download", self._start)
        self.cancel = button("Cancel", self.cancel_download, "danger")
        self.cancel.setEnabled(False)
        actions = QHBoxLayout()
        actions.addWidget(self.start)
        actions.addWidget(self.cancel)
        actions.addStretch()
        form.addRow("Video URL", self.url)
        form.addRow("Format", self.kind)
        form.addRow(actions)
        layout.addWidget(box)
        self.status = QLabel("Ready.")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Download progress will appear here.")
        layout.addWidget(self.log, stretch=1)

    def _start(self) -> None:
        url = self.url.text().strip()
        if not url:
            QMessageBox.warning(self, "URL required", "Paste a YouTube video URL first.")
            return
        self.log.clear()
        self.progress.setValue(0)
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.start_download(url, self.kind.currentIndex() == 1)

    def handle_progress(self, data: dict) -> None:
        event_type = data.get("type", "update")
        if event_type == "download":
            percent = float(data.get("percent", 0))
            self.progress.setValue(round(percent))
            self.status.setText(f"Downloading {percent:.1f}% — {data.get('speed', '')}, ETA {data.get('eta', '')}")
        elif event_type in ("extract", "converting"):
            self.status.setText("Processing media…")
        elif event_type == "starting":
            self.status.setText(f"Preparing: {data.get('title', '')}")
        elif event_type == "failed":
            self.log.append(data.get("message", "Download failed"))
        self.log.append(f"{event_type}: {data.get('title', '')}")

    def complete(self, success: bool, message: str) -> None:
        self.start.setEnabled(True)
        self.cancel.setEnabled(False)
        self.status.setText(message)
        if success:
            self.progress.setValue(100)


class HistoryPage(QWidget):
    def __init__(self, state: StateManager) -> None:
        super().__init__()
        self.state = state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Download history")
        title.setObjectName("title")
        layout.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, source, or video ID")
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Title", "Source", "Downloaded"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        items = self.state.get_all_downloaded_videos(self.search.text().strip() or None, limit=500)
        self.table.setRowCount(0)
        for row, item in enumerate(items):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["source"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["downloaded_at"]))


class SettingsPage(QWidget):
    changed = Signal()

    def __init__(self, config: Config, state: StateManager) -> None:
        super().__init__()
        self.config, self.state = config, state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Settings")
        title.setObjectName("title")
        layout.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        self.video_dir = self._path_field(form, "Video folder", config.base_video_dir)
        self.audio_dir = self._path_field(form, "Audio folder", config.base_audio_dir)
        self.playlist_dir = self._path_field(form, "Playlist folder", config.base_playlist_dir)
        self.podcast_dir = self._path_field(form, "Podcast folder", config.base_podcast_dir)
        self.resolution = QComboBox()
        self.resolution.addItems(SUPPORTED_RESOLUTIONS)
        self.resolution.setCurrentText(config.max_resolution)
        self.browser = QComboBox()
        self.browser.addItems(["auto", "none", *SUPPORTED_BROWSERS])
        self.browser.setCurrentText(config.browser)
        self.parallel = QSpinBox()
        self.parallel.setRange(1, 10)
        self.parallel.setValue(config.max_parallel_downloads)
        self.cleanup = QSpinBox()
        self.cleanup.setRange(1, 3650)
        self.cleanup.setValue(config.cleanup_days)
        self.filter_shorts = QCheckBox("Skip videos shorter than one minute")
        self.filter_shorts.setChecked(config.filter_shorts)
        form.addRow("Maximum resolution", self.resolution)
        form.addRow("Cookie browser", self.browser)
        form.addRow("Parallel downloads", self.parallel)
        form.addRow("Retention days", self.cleanup)
        form.addRow("Shorts filter", self.filter_shorts)
        form.addRow(button("Save settings", self.save))
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _path_field(self, form: QFormLayout, label: str, value: Path) -> QLineEdit:
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
            QMessageBox.critical(self, "Could not save settings", str(error))
            return
        QMessageBox.information(self, "Settings saved", "Your settings have been saved.")
        self.changed.emit()


class MainWindow(QMainWindow):
    """Desktop application shell shared by Windows, Linux, and macOS."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.logger = setup_logging(config.app_log_path, config.max_log_size, config.max_log_files)
        self.state = StateManager(config, self.logger)
        self.scanner = Scanner(config, self.state, self.logger)
        self.downloader = Downloader(config, self.state, self.scanner, self.logger)
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[object] = None

        self.setWindowTitle("Ytdaily")
        self.setMinimumSize(980, 650)
        self.resize(1180, 760)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self._build_tray()

    def _build_ui(self) -> None:
        root = QSplitter()
        root.setChildrenCollapsible(False)
        self.navigation = QListWidget()
        self.navigation.addItems(["Dashboard", "Channels", "Playlists", "Single download", "History", "Settings"])
        self.navigation.setFixedWidth(190)
        self.pages = QStackedWidget()
        self.dashboard = DashboardPage(self.config, self.state)
        self.channels = SourcesPage(self.state, "channel")
        self.playlists = SourcesPage(self.state, "playlist")
        self.download = DownloadPage(self.start_download, self.cancel_active_worker)
        self.history = HistoryPage(self.state)
        self.settings = SettingsPage(self.config, self.state)
        for page in (self.dashboard, self.channels, self.playlists, self.download, self.history, self.settings):
            self.pages.addWidget(page)
        root.addWidget(self.navigation)
        root.addWidget(self.pages)
        root.setStretchFactor(1, 1)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(f"Cookie browser: {detect_browser()}")
        self.navigation.currentRowChanged.connect(self.change_page)
        self.navigation.setCurrentRow(0)
        self.dashboard.run_requested.connect(self.start_auto_download)
        for page in (self.channels, self.playlists, self.settings):
            page.changed.connect(self.refresh_all)

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Ytdaily")
        show_action = QAction("Show Ytdaily", self)
        show_action.triggered.connect(self.showNormal)
        run_action = QAction("Scan and download", self)
        run_action.triggered.connect(self.start_auto_download)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu = self.tray.contextMenu() or __import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu(self)
        menu.addAction(show_action)
        menu.addAction(run_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda _: self.showNormal())
        self.tray.show()

    def change_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh()
        elif index == 4:
            self.history.refresh()

    def refresh_all(self) -> None:
        self.dashboard.refresh()
        self.channels.refresh()
        self.playlists.refresh()
        self.history.refresh()

    def _start_worker(self, worker: object, done: Callable[..., None]) -> None:
        if self.worker_thread is not None:
            QMessageBox.information(self, "Job already running", "Wait for the active job to finish or cancel it first.")
            return
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_worker)
        self.worker, self.worker_thread = worker, thread
        thread.start()

    def _clear_worker(self) -> None:
        self.worker = None
        self.worker_thread = None

    def start_download(self, url: str, is_audio: bool) -> None:
        worker = DownloadWorker(self.downloader, self.scanner, url, is_audio)
        worker.progress.connect(self.download.handle_progress)
        self._start_worker(worker, self._download_finished)

    def _download_finished(self, success: bool, message: str) -> None:
        self.download.complete(success, message)
        self.statusBar().showMessage(message, 5000)
        self.refresh_all()
        if self.tray is not None:
            self.tray.showMessage("Ytdaily", message)

    def start_auto_download(self) -> None:
        worker = AutoDownloadWorker(self.config, self.state, self.scanner, self.downloader)
        worker.status.connect(self._auto_status)
        worker.progress.connect(self.download.handle_progress)
        self.dashboard.run_button.setEnabled(False)
        self._start_worker(worker, self._auto_finished)

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

    def cancel_active_worker(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.statusBar().showMessage("Cancelling current job…")

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
