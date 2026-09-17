"""
Feature tests for Ytdaily TUI: Search/filter, history query, directory config.
"""

import tempfile
import unittest
from pathlib import Path

from ytdaily.config import Config
from ytdaily.core.state import StateManager
from ytdaily.ui.widgets.tables import create_item_table, create_history_table
from ytdaily.utils.cache import DirectoryDurationCache, format_duration_short


class TestTUIFeatures(unittest.TestCase):
    """Test new GUI/TUI capabilities."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.config = Config(
            base_video_dir=self.test_root / "Videos",
            base_audio_dir=self.test_root / "Music",
            log_dir=self.test_root / "logs",
        )
        self.state = StateManager(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_channel_playlist_search_filtering(self):
        channels = {
            "mreflow": "Matt Wolfe",
            "mkbhd": "Marques Brownlee",
            "fireship": "Fireship",
            "lexfridman": "Lex Fridman Podcast",
        }
        # Table with no filter
        t_all = create_item_table("All", channels)
        self.assertEqual(t_all.row_count, 4)

        # Table with filter matching "fireship"
        t_filtered = create_item_table("Filtered", channels, filter_query="fire")
        self.assertEqual(t_filtered.row_count, 1)

        # Table with filter matching "Wolfe"
        t_filtered2 = create_item_table("Filtered", channels, filter_query="Wolfe")
        self.assertEqual(t_filtered2.row_count, 1)

        # Table with no match
        t_empty = create_item_table("Filtered", channels, filter_query="nonexistent")
        self.assertEqual(t_empty.row_count, 1)  # 1 row for "No channels match"

    def test_download_history_query(self):
        # Insert test channel downloads
        self.state.update_channel_history("lexfridman", {
            "id": "vid001",
            "title": "Sam Altman on OpenAI and Future of AI",
            "url": "https://youtube.com/watch?v=vid001",
        })
        self.state.update_channel_history("mreflow", {
            "id": "vid002",
            "title": "Top 10 Open Source AI Tools You Must Try",
            "url": "https://youtube.com/watch?v=vid002",
        })

        # Query all
        all_hist = self.state.get_all_downloaded_videos()
        self.assertEqual(len(all_hist), 2)

        # Query filter by keyword
        ai_hist = self.state.get_all_downloaded_videos(query="OpenAI")
        self.assertEqual(len(ai_hist), 1)
        self.assertEqual(ai_hist[0]["video_id"], "vid001")

        # Query filter by channel id
        mreflow_hist = self.state.get_all_downloaded_videos(query="mreflow")
        self.assertEqual(len(mreflow_hist), 1)
        self.assertEqual(mreflow_hist[0]["video_id"], "vid002")

        # History table builder
        hist_table = create_history_table(ai_hist)
        self.assertEqual(hist_table.row_count, 1)

    def test_directory_cache_operations(self):
        cache_file = self.test_root / "test_cache.json"
        cache = DirectoryDurationCache(cache_file)

        dummy_file = self.test_root / "sample.mp4"
        dummy_file.write_text("dummy media content")

        self.assertIsNone(cache.get(dummy_file))
        cache.set(dummy_file, 128.5)
        cache.save()

        # Load in new cache instance
        cache2 = DirectoryDurationCache(cache_file)
        cached_dur = cache2.get(dummy_file)
        self.assertIsNotNone(cached_dur)
        self.assertEqual(cached_dur, 128.5)


if __name__ == "__main__":
    unittest.main()
