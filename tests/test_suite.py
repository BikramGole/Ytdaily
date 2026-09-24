"""
Comprehensive unit and integration tests for Ytdaily.
"""

import os
import tempfile
import unittest
from pathlib import Path

from ytdaily.config import Config
from ytdaily.core.downloader import Downloader
from ytdaily.core.scanner import Scanner
from ytdaily.core.sponsorblock import (
    build_video_download_command,
    build_audio_download_command,
    build_playlist_download_command,
)
from ytdaily.core.state import StateManager
from ytdaily.ui.widgets.tables import (
    create_item_table,
    create_summary_table,
    create_history_table,
    create_status_bar,
)
from ytdaily.ui.widgets.playlist_selector import selected_playlist_indices
from ytdaily.utils.browser import detect_browser, SUPPORTED_BROWSERS
from ytdaily.utils.cache import (
    format_duration,
    format_duration_short,
    DURATION_REGEX,
    DirectoryDurationCache,
)
from ytdaily.utils.system import check_dependencies, get_disk_space_info


class TestYtdailyCore(unittest.TestCase):
    """Test core business logic, configuration, and helpers."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.config = Config(
            base_video_dir=self.test_root / "Videos",
            base_audio_dir=self.test_root / "Music",
            base_playlist_dir=self.test_root / "Playlists",
            base_podcast_dir=self.test_root / "Podcasts",
            log_dir=self.test_root / "logs",
        )
        self.state = StateManager(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_duration_helpers(self):
        self.assertEqual(format_duration(0), "00:00")
        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3665), "01:01:05")
        self.assertEqual(format_duration(-1), "Unknown")
        self.assertEqual(format_duration(None), "Unknown")

        self.assertEqual(format_duration_short(45), "45sec")
        self.assertEqual(format_duration_short(125), "2min 5sec")
        self.assertEqual(format_duration_short(3600), "1hr")
        self.assertEqual(format_duration_short(3660), "1hr 1min")

    def test_duration_regex(self):
        self.assertTrue(DURATION_REGEX.search("YT_feed -28hr 17min"))
        self.assertTrue(DURATION_REGEX.search("My Channel -45sec"))
        self.assertTrue(DURATION_REGEX.search("Music -2.5hr"))
        self.assertFalse(DURATION_REGEX.search("Regular Video Title"))

    def test_config_validation(self):
        cfg = Config(
            max_resolution="9999",
            max_parallel_downloads=99,
            cleanup_days=-5,
            browser="nonexistent_browser",
            log_dir=self.test_root / "logs2",
        )
        issues = cfg.validate()
        self.assertTrue(len(issues) > 0)
        self.assertEqual(cfg.max_resolution, "720")
        self.assertEqual(cfg.max_parallel_downloads, 3)
        self.assertEqual(cfg.cleanup_days, 60)
        self.assertEqual(cfg.browser, "auto")

    def test_state_manager_operations(self):
        self.state.channels["testchan"] = "Test Channel"
        self.state.playlists["https://youtube.com/playlist?list=123"] = "Test Playlist"
        self.state.save_config()

        # Reload state in fresh instance
        new_state = StateManager(self.config)
        self.assertIn("testchan", new_state.channels)
        self.assertEqual(new_state.channels["testchan"], "Test Channel")
        self.assertIn("https://youtube.com/playlist?list=123", new_state.playlists)

        # Video history tracking
        video_data = {"id": "vid123", "title": "Great Video", "url": "https://youtube.com/watch?v=vid123"}
        self.assertFalse(new_state.is_video_downloaded("testchan", "vid123"))
        new_state.update_channel_history("testchan", video_data)
        self.assertTrue(new_state.is_video_downloaded("testchan", "vid123"))

        # Resume state operations
        new_state.update_resume_state("video", "vid123", {"progress": 45})
        resume = new_state.get_resume_state("video", "vid123")
        self.assertIsNotNone(resume)
        self.assertEqual(resume["progress"], 45)
        new_state.clear_resume_state("video", "vid123")
        self.assertIsNone(new_state.get_resume_state("video", "vid123"))

        # Query all downloaded videos
        history_list = new_state.get_all_downloaded_videos(query="Great")
        self.assertEqual(len(history_list), 1)
        self.assertEqual(history_list[0]["title"], "Great Video")

    def test_sponsorblock_command_generation(self):
        video_cmd = build_video_download_command(
            self.config,
            "https://youtube.com/watch?v=12345",
            self.config.current_video_dir,
            skip_subs=False,
            resume=True,
        )
        self.assertIn("yt-dlp", video_cmd)
        self.assertIn("--sponsorblock-remove", video_cmd)
        self.assertIn("--continue", video_cmd)
        self.assertIn("--embed-subs", video_cmd)

        audio_cmd = build_audio_download_command(
            self.config,
            "https://youtube.com/watch?v=12345",
            self.config.current_audio_dir,
            resume=False,
        )
        self.assertIn("--extract-audio", audio_cmd)
        self.assertIn("--audio-format", audio_cmd)
        self.assertIn("mp3", audio_cmd)
        self.assertIn("--no-continue", audio_cmd)

        playlist_cmd, _ = build_playlist_download_command(
            self.config,
            "https://youtube.com/playlist?list=12345",
            "Test Playlist",
            playlist_items=[3, 1, 3],
        )
        selected_index = playlist_cmd.index("--playlist-items")
        self.assertEqual(playlist_cmd[selected_index + 1], "1,3")

    def test_playlist_selection_uses_playlist_positions(self):
        videos = [
            {"title": "One", "playlist_index": 1},
            {"title": "Three", "playlist_index": 3},
        ]
        self.assertEqual(selected_playlist_indices(videos, {2}), [3])

    def test_downloader_progress_parser(self):
        scanner = Scanner(self.config, self.state)
        downloader = Downloader(self.config, self.state, scanner)

        dl_line = "[download]  45.2% of ~  12.50MiB at    1.20MiB/s ETA 00:05"
        parsed = downloader.parse_progress(dl_line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["type"], "download")
        self.assertEqual(parsed["percent"], "45.2")
        self.assertEqual(parsed["eta"], "00:05")

        playlist_line = "[download] Downloading item 3 of 10"
        parsed_pl = downloader.parse_progress(playlist_line)
        self.assertIsNotNone(parsed_pl)
        self.assertEqual(parsed_pl["type"], "playlist_progress")
        self.assertEqual(parsed_pl["current"], "3")
        self.assertEqual(parsed_pl["total"], "10")

    def test_ui_table_builders(self):
        items = {"mreflow": "Matt Wolfe", "mkbhd": "Marques Brownlee"}
        item_table = create_item_table("Channels", items, item_type="Channel")
        self.assertEqual(item_table.row_count, 2)

        summary_table = create_summary_table(5, 12.5)
        self.assertEqual(summary_table.row_count, 3)

        status_bar = create_status_bar(self.config, self.state)
        self.assertIsNotNone(status_bar)

    def test_system_and_browser(self):
        ok, missing = check_dependencies()
        self.assertTrue(ok)
        self.assertEqual(len(missing), 0)

        disk_info = get_disk_space_info(self.test_root)
        self.assertIn("total_gb", disk_info)
        self.assertIn("free_gb", disk_info)

        browser = detect_browser()
        self.assertIsInstance(browser, str)


if __name__ == "__main__":
    unittest.main()
