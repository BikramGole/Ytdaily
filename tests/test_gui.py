"""Smoke coverage for the optional PySide6 desktop interface."""

import os
import tempfile
import unittest
import logging
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
            for h in logging.getLogger("ytdaily").handlers[:]:
                h.close()
                logging.getLogger("ytdaily").removeHandler(h)
        window.deleteLater()

    def test_playlist_picker_needs_selection_before_download(self):
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
            playlist = window.download.playlist

            playlist.display_playlist(
                {
                    "info": {"title": "Sample", "uploader": "Creator", "video_count": 3},
                    "videos": [
                        {"title": "One", "playlist_index": 1},
                        {"title": "Two", "playlist_index": 2},
                        {"title": "Three", "playlist_index": 3},
                    ],
                }
            )

            self.assertEqual(playlist.table.rowCount(), 3)
            self.assertEqual(playlist.selected_indices(), [])
            self.assertFalse(playlist.download_button.isEnabled())
            self.assertTrue(playlist.fetch_button.isEnabled())

            playlist._select_all()
            self.assertEqual(playlist.selected_indices(), [1, 2, 3])
            self.assertTrue(playlist.download_button.isEnabled())

            playlist._clear_selection()
            self.assertEqual(playlist.selected_indices(), [])
            self.assertFalse(playlist.download_button.isEnabled())

            if window.tray is not None:
                window.tray.hide()
            for h in logging.getLogger("ytdaily").handlers[:]:
                h.close()
                logging.getLogger("ytdaily").removeHandler(h)
        window.deleteLater()
