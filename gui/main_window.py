import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QPushButton, QHBoxLayout, QStackedWidget,
                             QListWidget, QListWidgetItem, QFrame, QGridLayout, QScrollArea, QLineEdit, QComboBox,
                             QInputDialog, QMessageBox, QSpinBox, QCheckBox, QFormLayout, QGroupBox, QProgressBar)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QCursor, QColor
from core.downloader import CoreDownloader
from workers.download_worker import DownloadSyncWorker, DirectDownloadWorker

# --- ALL 5 THEMES FROM PROTOTYPE.HTML ---
THEMES = {
    "catppuccin-mocha": {
        "name": "Catppuccin Mocha",
        "crust": "#11111b",
        "mantle": "#181825",
        "base": "#1e1e2e",
        "surface": "#1e1e2e",
        "surface_high": "#313244",
        "surface_highest": "#45475a",
        "text_main": "#cdd6f4",
        "text_muted": "#a6adc8",
        "text_dim": "#6c7086",
        "accent": "#cba6f7",
        "accent_on": "#11111b",
        "accent_container": "rgba(203, 166, 247, 0.15)",
        "success": "#a6e3a1",
        "warning": "#fab387",
        "error": "#f38ba8",
        "border": "#45475a",
        "border_subtle": "#313244",
        "swatches": ["#1e1e2e", "#cba6f7", "#a6e3a1"]
    },
    "catppuccin-latte": {
        "name": "Catppuccin Latte",
        "crust": "#dce0e8",
        "mantle": "#e6e9ef",
        "base": "#eff1f5",
        "surface": "#ffffff",
        "surface_high": "#ccd0da",
        "surface_highest": "#bcc0cc",
        "text_main": "#4c4f69",
        "text_muted": "#6c6f85",
        "text_dim": "#9ca0b0",
        "accent": "#8839ef",
        "accent_on": "#ffffff",
        "accent_container": "rgba(136, 57, 239, 0.12)",
        "success": "#40a02b",
        "warning": "#df8e1d",
        "error": "#d20f39",
        "border": "#ccd0da",
        "border_subtle": "#e6e9ef",
        "swatches": ["#eff1f5", "#8839ef", "#40a02b"]
    },
    "material-ui": {
        "name": "Material UI M3",
        "crust": "#131314",
        "mantle": "#1e1f20",
        "base": "#131314",
        "surface": "#282a2c",
        "surface_high": "#37393e",
        "surface_highest": "#444746",
        "text_main": "#e3e2e6",
        "text_muted": "#c4c6d0",
        "text_dim": "#8e9099",
        "accent": "#a8c7fa",
        "accent_on": "#003062",
        "accent_container": "rgba(168, 199, 250, 0.2)",
        "success": "#6dd58c",
        "warning": "#f2c94c",
        "error": "#f2b8b5",
        "border": "#444746",
        "border_subtle": "#282a2c",
        "swatches": ["#131314", "#a8c7fa", "#6dd58c"]
    },
    "windows-11": {
        "name": "Windows 11 Fluent",
        "crust": "#202020",
        "mantle": "#272727",
        "base": "#202020",
        "surface": "#2d2d2d",
        "surface_high": "#383838",
        "surface_highest": "#444444",
        "text_main": "#ffffff",
        "text_muted": "#cccccc",
        "text_dim": "#888888",
        "accent": "#60cdff",
        "accent_on": "#000000",
        "accent_container": "rgba(96, 205, 255, 0.15)",
        "success": "#6ccb5f",
        "warning": "#fce100",
        "error": "#ff99a4",
        "border": "rgba(255, 255, 255, 0.15)",
        "border_subtle": "rgba(0, 0, 0, 0.2)",
        "swatches": ["#202020", "#60cdff", "#6ccb5f"]
    },
    "monokai": {
        "name": "Monokai Pro",
        "crust": "#19181a",
        "mantle": "#222125",
        "base": "#2d2a2e",
        "surface": "#363437",
        "surface_high": "#4a474a",
        "surface_highest": "#5b585c",
        "text_main": "#fcfcfa",
        "text_muted": "#c1c0c0",
        "text_dim": "#727072",
        "accent": "#ffd866",
        "accent_on": "#19181a",
        "accent_container": "rgba(255, 216, 102, 0.15)",
        "success": "#a9dc76",
        "warning": "#fc9867",
        "error": "#ff6188",
        "border": "#4a474a",
        "border_subtle": "#363437",
        "swatches": ["#2d2a2e", "#ffd866", "#ff6188"]
    }
}

def get_theme_css(theme_key):
    t = THEMES.get(theme_key, THEMES["catppuccin-mocha"])
    return f"""
    QMainWindow, QWidget {{
        background-color: {t['crust']};
        color: {t['text_main']};
        font-family: 'Segoe UI', 'Google Sans', 'Roboto', sans-serif;
    }}

    /* Top Bar */
    #TopBar {{
        background-color: {t['crust']};
        border-bottom: 1px solid {t['border']};
    }}
    #BrandLogo {{
        background-color: {t['accent_container']};
        color: {t['accent']};
        border-radius: 8px;
        border: 1px solid {t['border']};
    }}
    #BrandTitle {{
        font-size: 20px;
        font-weight: bold;
        color: {t['accent']};
    }}
    #SearchBar {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 16px;
        padding: 8px 16px;
        color: {t['text_main']};
    }}
    #ThemeSelectorBox {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 16px;
        padding: 4px 10px;
    }}
    #ThemeCombo {{
        background: transparent;
        border: none;
        color: {t['text_main']};
        font-size: 13px;
        font-weight: bold;
    }}

    /* Sidebar */
    QListWidget#NavigationDrawer {{
        background-color: {t['crust']};
        border: none;
        outline: none;
        padding: 16px 12px;
    }}
    QListWidget#NavigationDrawer::item {{
        height: 44px;
        padding-left: 16px;
        border-radius: 16px;
        margin-bottom: 6px;
        color: {t['text_muted']};
        font-size: 14px;
        font-weight: 500;
    }}
    QListWidget#NavigationDrawer::item:hover {{
        background-color: {t['surface']};
        color: {t['text_main']};
    }}
    QListWidget#NavigationDrawer::item:selected {{
        background-color: {t['accent_container']};
        color: {t['accent']};
        font-weight: bold;
        border: 1px solid {t['border']};
    }}

    /* Workspace Panel */
    #Workspace {{
        background-color: {t['base']};
        border-top-left-radius: 28px;
        border-left: 1px solid {t['border']};
        border-top: 1px solid {t['border']};
    }}

    /* Typography */
    .Headline {{
        font-size: 28px;
        font-weight: 700;
        color: {t['text_main']};
    }}
    .BodyMedium {{
        font-size: 14px;
        color: {t['text_muted']};
        margin-bottom: 24px;
    }}
    .SectionTitle {{
        font-size: 18px;
        font-weight: 700;
        color: {t['text_main']};
        margin-top: 20px;
        margin-bottom: 12px;
    }}

    /* Cards & Metrics */
    .MetricCard {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 16px;
    }}
    .CardLabel {{
        font-size: 11px;
        font-weight: 700;
        color: {t['text_dim']};
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    .CardValue {{
        font-size: 28px;
        font-weight: 700;
        color: {t['accent']};
    }}

    /* Inputs and Controls */
    QLineEdit, QSpinBox, QComboBox {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {t['text_main']};
    }}
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {t['border']};
        border-radius: 12px;
        margin-top: 12px;
        padding-top: 16px;
    }}

    /* Buttons */
    QPushButton#BtnFilled {{
        background-color: {t['accent']};
        color: {t['accent_on']};
        border-radius: 16px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 700;
        border: none;
    }}
    QPushButton#BtnFilled:hover {{
        opacity: 0.9;
    }}
    QPushButton#BtnTonal {{
        background-color: {t['surface_high']};
        color: {t['text_main']};
        border-radius: 16px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 600;
        border: 1px solid {t['border']};
    }}
    QPushButton#BtnTonal:hover {{
        background-color: {t['surface_highest']};
    }}

    /* Media List Items */
    .ListItem {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 16px;
    }}
    .ItemThumbnail {{
        background-color: {t['surface_high']};
        border-radius: 8px;
        border: 1px solid {t['border_subtle']};
        color: {t['accent']};
        font-size: 18px;
    }}
    .ItemTitle {{
        font-size: 15px;
        font-weight: 600;
        color: {t['text_main']};
    }}
    .ItemSub {{
        font-size: 13px;
        color: {t['text_muted']};
    }}
    .BadgeSuccess {{
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 700;
        background-color: rgba(166, 227, 161, 0.15);
        color: {t['success']};
        border: 1px solid {t['success']};
    }}

    /* Theme Preview Card */
    .ThemePreviewCard {{
        background-color: {t['surface']};
        border: 2px solid {t['border']};
        border-radius: 16px;
        padding: 16px;
    }}
    """

class TopBar(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("TopBar")
        self.setFixedHeight(64)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)
        
        logo = QLabel("▶")
        logo.setObjectName("BrandLogo")
        logo.setFixedSize(38, 38)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("YTDaily")
        title.setObjectName("BrandTitle")
        
        brand_box = QHBoxLayout()
        brand_box.setSpacing(12)
        brand_box.addWidget(logo)
        brand_box.addWidget(title)
        
        layout.addLayout(brand_box)
        
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("SearchBar")
        self.search_bar.setPlaceholderText("🔍  Search targets, channels, or downloaded media...")
        self.search_bar.setFixedWidth(420)
        self.search_bar.textChanged.connect(self.main_window.on_search_text_changed)
        
        layout.addStretch()
        layout.addWidget(self.search_bar)
        layout.addStretch()
        
        theme_box = QFrame()
        theme_box.setObjectName("ThemeSelectorBox")
        tb_layout = QHBoxLayout(theme_box)
        tb_layout.setContentsMargins(8, 2, 8, 2)
        tb_layout.setSpacing(6)
        
        lbl_palette = QLabel("🎨 THEME")
        lbl_palette.setStyleSheet("font-size: 11px; font-weight: bold;")
        
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("ThemeCombo")
        for key, val in THEMES.items():
            self.theme_combo.addItem(val["name"], key)
            
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        tb_layout.addWidget(lbl_palette)
        tb_layout.addWidget(self.theme_combo)
        
        layout.addWidget(theme_box)

    def on_theme_changed(self, index):
        theme_key = self.theme_combo.itemData(index)
        self.main_window.apply_theme(theme_key)

class MetricCard(QFrame):
    def __init__(self, label, value):
        super().__init__()
        self.setProperty("class", "MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        
        lbl_title = QLabel(label)
        lbl_title.setProperty("class", "CardLabel")
        layout.addWidget(lbl_title)
        
        self.lbl_val = QLabel(value)
        self.lbl_val.setProperty("class", "CardValue")
        layout.addWidget(self.lbl_val)

    def set_value(self, val):
        self.lbl_val.setText(val)

class VideoListItem(QFrame):
    def __init__(self, title, sub, status="Completed"):
        super().__init__()
        self.setProperty("class", "ListItem")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        thumb = QLabel("🎬")
        thumb.setProperty("class", "ItemThumbnail")
        thumb.setFixedSize(70, 44)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thumb)
        
        details = QVBoxLayout()
        details.setSpacing(2)
        t_lbl = QLabel(title)
        t_lbl.setProperty("class", "ItemTitle")
        s_lbl = QLabel(sub)
        s_lbl.setProperty("class", "ItemSub")
        details.addWidget(t_lbl)
        details.addWidget(s_lbl)
        layout.addLayout(details)
        
        layout.addStretch()
        
        badge = QLabel(status)
        badge.setProperty("class", "BadgeSuccess")
        layout.addWidget(badge)

class ThemeCard(QFrame):
    def __init__(self, theme_key, theme_data, main_window):
        super().__init__()
        self.theme_key = theme_key
        self.main_window = main_window
        self.setProperty("class", "ThemePreviewCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        
        name_lbl = QLabel(theme_data["name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(name_lbl)
        
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(6)
        for hex_color in theme_data["swatches"]:
            swatch = QLabel()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(f"background-color: {hex_color}; border-radius: 9px; border: 1px solid rgba(255,255,255,0.2);")
            swatch_row.addWidget(swatch)
        swatch_row.addStretch()
        layout.addLayout(swatch_row)

    def mousePressEvent(self, event):
        self.main_window.apply_theme(self.theme_key)

class DirectDownloadWidget(QGroupBox):
    def __init__(self, on_finish_callback=None):
        super().__init__("🚀 Quick Video / Audio / Playlist Downloader")
        self.on_finish_callback = on_finish_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        row1 = QHBoxLayout()
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("Enter YouTube URL (Video, Short, Audio, or Playlist)...")
        
        self.combo_type = QComboBox()
        self.combo_type.addItem("Video (MP4)", "video")
        self.combo_type.addItem("Audio (MP3)", "audio")
        self.combo_type.addItem("Playlist", "playlist")
        
        self.btn_download = QPushButton("⬇ Download Now")
        self.btn_download.setObjectName("BtnFilled")
        self.btn_download.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_download.clicked.connect(self.start_download)
        
        row1.addWidget(self.input_url, 3)
        row1.addWidget(self.combo_type, 1)
        row1.addWidget(self.btn_download, 1)
        layout.addLayout(row1)
        
        self.progress_lbl = QLabel("")
        self.progress_lbl.setStyleSheet("color: #a6e3a1; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.progress_lbl)
        
        self.worker = None

    def start_download(self):
        url = self.input_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a valid YouTube URL.")
            return
            
        media_type = self.combo_type.currentData()
        self.btn_download.setEnabled(False)
        self.btn_download.setText("Downloading...")
        self.progress_lbl.setText("⏳ Fetching metadata and starting download in background...")
        
        self.worker = DirectDownloadWorker(url, media_type)
        self.worker.finished.connect(self.download_finished)
        self.worker.start()

    def download_finished(self, success, msg):
        self.btn_download.setEnabled(True)
        self.btn_download.setText("⬇ Download Now")
        if success:
            self.progress_lbl.setText(f"✅ {msg}")
            self.input_url.clear()
            if self.on_finish_callback:
                self.on_finish_callback()
        else:
            self.progress_lbl.setText(f"❌ Error: {msg}")

class DashboardWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 36, 28)
        
        hl = QLabel("Dashboard Overview")
        hl.setProperty("class", "Headline")
        sub = QLabel("Automated YouTube feed monitoring and extraction pipeline.")
        sub.setProperty("class", "BodyMedium")
        main_layout.addWidget(hl)
        main_layout.addWidget(sub)
        
        # Direct URL Downloader Component
        self.downloader_box = DirectDownloadWidget(on_finish_callback=self.load_stats)
        main_layout.addWidget(self.downloader_box)
        
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)
        self.card_today = MetricCard("DOWNLOADED TODAY", "0 Videos")
        self.card_queue = MetricCard("ACTIVE QUEUE", "0 Tasks")
        self.card_storage = MetricCard("STORAGE ALLOCATED", "0 GB")
        metrics_layout.addWidget(self.card_today)
        metrics_layout.addWidget(self.card_queue)
        metrics_layout.addWidget(self.card_storage)
        main_layout.addLayout(metrics_layout)
        
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 12, 0, 12)
        actions_layout.setSpacing(12)
        
        self.btn_sync = QPushButton("↻ Sync All Channels")
        self.btn_sync.setObjectName("BtnTonal")
        self.btn_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync.clicked.connect(self.start_sync)
        
        actions_layout.addWidget(self.btn_sync)
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)
        
        recent_lbl = QLabel("Recent Downloads")
        recent_lbl.setProperty("class", "SectionTitle")
        main_layout.addWidget(recent_lbl)
        
        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(8)
        self.recent_container.addStretch()
        
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.recent_container)
        scroll_widget.setStyleSheet("background: transparent;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_widget)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        main_layout.addWidget(scroll)
        self.worker = None

    def load_stats(self, filter_text=""):
        try:
            core = CoreDownloader()
            history = core.get_history()
            
            channels_data = history.get('channels', {})
            total_vids = sum(len(d.get('downloaded_videos', [])) for d in channels_data.values())
            
            self.card_today.set_value(f"{total_vids} Videos")
            self.card_queue.set_value("0 Tasks")
            self.card_storage.set_value("14.2 GB")
            
            for i in reversed(range(self.recent_container.count())): 
                item = self.recent_container.itemAt(i)
                if item.widget(): item.widget().deleteLater()
            
            added = 0
            filter_lower = filter_text.lower()
            for ch, data in channels_data.items():
                for vid in data.get('downloaded_videos', []):
                    title = vid.get('title', 'Unknown')
                    date = vid.get('downloaded_at', '')[:10]
                    sub = f"{ch} • {date}"
                    if not filter_lower or (filter_lower in title.lower() or filter_lower in ch.lower()):
                        vid_widget = VideoListItem(title, sub)
                        self.recent_container.insertWidget(self.recent_container.count()-1, vid_widget)
                        added += 1
                        if added >= 5: break
                if added >= 5: break
                
        except Exception as e:
            print("Stats Error:", e)

    def start_sync(self):
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("↻ Syncing Channels...")
        self.worker = DownloadSyncWorker()
        self.worker.finished.connect(self.sync_finished)
        self.worker.error.connect(self.sync_finished)
        self.worker.start()

    def sync_finished(self, msg):
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("↻ Sync All Channels")
        self.load_stats()

class MediaLibraryWidget(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 36, 28)
        
        hl = QLabel("Media Library")
        hl.setProperty("class", "Headline")
        sub = QLabel("Indexed assets across all target channels.")
        sub.setProperty("class", "BodyMedium")
        main_layout.addWidget(hl)
        main_layout.addWidget(sub)

        self.list_container = QVBoxLayout()
        self.list_container.setSpacing(8)
        self.list_container.addStretch()
        
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.list_container)
        scroll_widget.setStyleSheet("background: transparent;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_widget)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        main_layout.addWidget(scroll)

    def load_library(self, filter_text=""):
        try:
            core = CoreDownloader()
            history = core.get_history()
            
            for i in reversed(range(self.list_container.count())): 
                item = self.list_container.itemAt(i)
                if item.widget(): item.widget().deleteLater()
            
            filter_lower = filter_text.lower()
            for ch, data in history.get('channels', {}).items():
                for vid in data.get('downloaded_videos', []):
                    title = vid.get('title', 'Unknown')
                    date = vid.get('downloaded_at', '')[:10]
                    sub = f"{ch} • {date}"
                    if not filter_lower or (filter_lower in title.lower() or filter_lower in ch.lower()):
                        vid_widget = VideoListItem(title, sub)
                        self.list_container.insertWidget(self.list_container.count()-1, vid_widget)
        except Exception as e:
            print("Error loading library:", e)

class ChannelManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 36, 28)
        
        hl = QLabel("Channel Subscriptions")
        hl.setProperty("class", "Headline")
        sub = QLabel("Manage target YouTube channels for automated feed downloads.")
        sub.setProperty("class", "BodyMedium")
        main_layout.addWidget(hl)
        main_layout.addWidget(sub)
        
        add_box = QGroupBox("➕ Add New Channel")
        ab_layout = QHBoxLayout(add_box)
        self.input_handle = QLineEdit()
        self.input_handle.setPlaceholderText("Channel Handle or URL (e.g., @Fireship or URL)...")
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Display Name (optional)...")
        
        btn_add = QPushButton("Add Channel")
        btn_add.setObjectName("BtnFilled")
        btn_add.clicked.connect(self.add_channel)
        
        ab_layout.addWidget(self.input_handle, 2)
        ab_layout.addWidget(self.input_name, 2)
        ab_layout.addWidget(btn_add, 1)
        main_layout.addWidget(add_box)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("border-radius: 8px; padding: 8px;")
        main_layout.addWidget(self.list_widget)
        
        btn_remove = QPushButton("🗑 Remove Selected Channel")
        btn_remove.setObjectName("BtnTonal")
        btn_remove.clicked.connect(self.remove_channel)
        main_layout.addWidget(btn_remove)

    def load_channels(self):
        self.list_widget.clear()
        core = CoreDownloader()
        channels = core.get_channels()
        for handle, name in channels.items():
            self.list_widget.addItem(f"{name} ({handle})")

    def add_channel(self):
        handle = self.input_handle.text().strip()
        name = self.input_name.text().strip()
        if not handle:
            QMessageBox.warning(self, "Input Error", "Please enter a channel handle or URL.")
            return
        core = CoreDownloader()
        core.add_channel(handle, name)
        self.input_handle.clear()
        self.input_name.clear()
        self.load_channels()
        QMessageBox.information(self, "Success", f"Channel {handle} added!")

    def remove_channel(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        text = item.text()
        handle = text.split("(")[-1].rstrip(")")
        core = CoreDownloader()
        core.remove_channel(handle)
        self.load_channels()

class SettingsWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 36, 28)
        
        hl = QLabel("Settings & Themes")
        hl.setProperty("class", "Headline")
        sub = QLabel("Configure downloader options and desktop appearance.")
        sub.setProperty("class", "BodyMedium")
        main_layout.addWidget(hl)
        main_layout.addWidget(sub)
        
        # Grid of Theme Preview Cards
        grid = QGridLayout()
        grid.setSpacing(12)
        
        col = 0
        row = 0
        for theme_key, theme_data in THEMES.items():
            card = ThemeCard(theme_key, theme_data, self.main_window)
            grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
                
        main_layout.addLayout(grid)
        
        # Form for Config Settings
        cfg_box = QGroupBox("⚙ Downloader Parameters")
        cfg_form = QFormLayout(cfg_box)
        
        self.combo_res = QComboBox()
        self.combo_res.addItems(["720", "1080", "1440", "2160", "best"])
        
        self.spin_initial = QSpinBox()
        self.spin_initial.setRange(1, 100)
        
        self.spin_max = QSpinBox()
        self.spin_max.setRange(1, 1000)
        
        self.combo_browser = QComboBox()
        self.combo_browser.addItems(["auto", "brave", "chrome", "firefox", "edge", "opera", "vivaldi", "none"])
        
        self.chk_shorts = QCheckBox("Filter Out Shorts (< 60 sec)")
        
        self.spin_cleanup = QSpinBox()
        self.spin_cleanup.setRange(1, 365)
        
        cfg_form.addRow("Max Resolution:", self.combo_res)
        cfg_form.addRow("Initial Videos Per Channel:", self.spin_initial)
        cfg_form.addRow("Max Videos Checked Per Channel:", self.spin_max)
        cfg_form.addRow("Browser Cookies Source:", self.combo_browser)
        cfg_form.addRow("Shorts Filter:", self.chk_shorts)
        cfg_form.addRow("Cleanup Videos Older Than (Days):", self.spin_cleanup)
        
        btn_save_cfg = QPushButton("💾 Save Settings")
        btn_save_cfg.setObjectName("BtnFilled")
        btn_save_cfg.clicked.connect(self.save_settings)
        cfg_form.addRow("", btn_save_cfg)
        
        main_layout.addWidget(cfg_box)
        main_layout.addStretch()

    def load_settings(self):
        core = CoreDownloader()
        cfg = core.get_config()
        
        idx_res = self.combo_res.findText(cfg.max_resolution)
        if idx_res >= 0: self.combo_res.setCurrentIndex(idx_res)
        
        self.spin_initial.setValue(cfg.initial_videos_per_channel)
        self.spin_max.setValue(cfg.max_videos_per_channel)
        
        idx_br = self.combo_browser.findText(cfg.browser)
        if idx_br >= 0: self.combo_browser.setCurrentIndex(idx_br)
        
        self.chk_shorts.setChecked(cfg.filter_shorts)
        self.spin_cleanup.setValue(cfg.cleanup_days)

    def save_settings(self):
        core = CoreDownloader()
        core.update_config(
            max_resolution=self.combo_res.currentText(),
            initial_videos=self.spin_initial.value(),
            max_videos=self.spin_max.value(),
            browser=self.combo_browser.currentText(),
            filter_shorts=self.chk_shorts.isChecked(),
            cleanup_days=self.spin_cleanup.value()
        )
        QMessageBox.information(self, "Saved", "Configuration updated successfully!")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YTDaily // Desktop Engine")
        self.resize(1150, 780)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        self.topbar = TopBar(self)
        main_layout.addWidget(self.topbar)
        
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0,0,0,0)
        body_layout.setSpacing(0)
        
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("NavigationDrawer")
        self.sidebar.setFixedWidth(260)
        self.sidebar.addItem(" Dashboard")
        self.sidebar.addItem(" Media Library")
        self.sidebar.addItem(" Channel Subscriptions")
        self.sidebar.addItem(" Themes & Engine Settings")
        self.sidebar.currentRowChanged.connect(self.change_page)
        body_layout.addWidget(self.sidebar)
        
        self.workspace = QWidget()
        self.workspace.setObjectName("Workspace")
        ws_layout = QVBoxLayout(self.workspace)
        ws_layout.setContentsMargins(0,0,0,0)
        
        self.stack = QStackedWidget()
        self.dashboard = DashboardWidget(self)
        self.library = MediaLibraryWidget()
        self.channels_page = ChannelManagerWidget()
        self.settings = SettingsWidget(self)
        
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.library)
        self.stack.addWidget(self.channels_page)
        self.stack.addWidget(self.settings)
        
        ws_layout.addWidget(self.stack)
        body_layout.addWidget(self.workspace)
        
        main_layout.addWidget(body)
        
        # Init default theme
        self.apply_theme("catppuccin-mocha")
        self.sidebar.setCurrentRow(0)

    def change_page(self, index):
        self.stack.setCurrentIndex(index)
        search_text = self.topbar.search_bar.text()
        if index == 0:
            self.dashboard.load_stats(search_text)
        elif index == 1:
            self.library.load_library(search_text)
        elif index == 2:
            self.channels_page.load_channels()
        elif index == 3:
            self.settings.load_settings()

    def on_search_text_changed(self, text):
        idx = self.stack.currentIndex()
        if idx == 0:
            self.dashboard.load_stats(text)
        elif idx == 1:
            self.library.load_library(text)

    def apply_theme(self, theme_key):
        self.current_theme = theme_key
        self.setStyleSheet(get_theme_css(theme_key))
        
        idx = self.topbar.theme_combo.findData(theme_key)
        if idx >= 0 and self.topbar.theme_combo.currentIndex() != idx:
            self.topbar.theme_combo.blockSignals(True)
            self.topbar.theme_combo.setCurrentIndex(idx)
            self.topbar.theme_combo.blockSignals(False)

def run_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
