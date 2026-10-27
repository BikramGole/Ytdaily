"""Smoke coverage for the optional PySide6 desktop interface."""

import os
import tempfile
import unittest
import logging
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


try:
    from PySide6.QtWidgets import QApplication
    from ytdaily.config import Config
    from ytdaily.gui.window import MainWindow
    from ytdaily.gui.workers import AutoDownloadWorker
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

    def test_auto_download_stops_at_already_downloaded_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(
                base_video_dir=root / "Videos",
                base_audio_dir=root / "Music",
                base_playlist_dir=root / "Playlists",
                base_podcast_dir=root / "Podcasts",
                log_dir=root / "state",
            )
            state = MagicMock()
            state.channels = {"chan": "Channel"}
            state.playlists = {}
            state.is_first_run.return_value = False
            state.download_history = {"channels": {"chan": "known"}, "playlists": {}}
            state.is_video_downloaded.side_effect = lambda source, vid: vid == "known"

            scanner = MagicMock()
            scanner.get_all_recent_videos.return_value = [
                {"id": "new1", "title": "New 1", "duration": 300},
                {"id": "new2", "title": "New 2", "duration": 300},
                {"id": "known", "title": "Old", "duration": 300},
                {"id": "older", "title": "Older", "duration": 300},
            ]
            downloader = MagicMock()
            downloader.download_video.return_value = (True, "new1")

            worker = AutoDownloadWorker(config, state, scanner, downloader)
            results = []
            worker.finished.connect(lambda count, message: results.append((count, message)))

            worker.run()

            downloaded_ids = [call.args[0]["id"] for call in downloader.download_video.call_args_list]
            self.assertEqual(downloaded_ids, ["new1", "new2"])
            self.assertEqual(results, [(2, "Downloaded 2 new item(s).")])

            for h in logging.getLogger("ytdaily").handlers[:]:
                h.close()
                logging.getLogger("ytdaily").removeHandler(h)

    def test_single_download_preview_display(self):
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
            panel = window.download.single
            self.assertTrue(panel.preview_box.isHidden())

            panel.display_preview({
                "title": "Sample Clip",
                "uploader": "Test Channel",
                "duration": 120,
                "url": "https://example.com/video",
            })
            self.assertFalse(panel.preview_box.isHidden())
            self.assertEqual(panel.preview_title.text(), "Sample Clip")
            self.assertIn("Test Channel", panel.preview_uploader.text())

            if window.tray is not None:
                window.tray.hide()
            for h in logging.getLogger("ytdaily").handlers[:]:
                h.close()
                logging.getLogger("ytdaily").removeHandler(h)
        window.deleteLater()
