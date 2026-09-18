"""Smoke coverage for the optional PySide6 desktop interface."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


try:
    from PySide6.QtWidgets import QApplication
    from ytdaily.config import Config
    from ytdaily.gui.window import MainWindow
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class TestDesktopGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_has_all_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(
                base_video_dir=root / "Videos",
                base_audio_dir=root / "Music",
                base_playlist_dir=root / "Playlists",
                base_podcast_dir=root / "Podcasts",
                log_dir=root / "state",
            )
            window = MainWindow(config)
            self.assertEqual(window.windowTitle(), "Ytdaily")
            self.assertEqual(window.pages.count(), 6)
            if window.tray is not None:
                window.tray.hide()
            window.deleteLater()
