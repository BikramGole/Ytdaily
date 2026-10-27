"""
Unit tests for terminal and GUI thumbnail rendering utilities.
"""

import io
import os
import unittest
from unittest.mock import patch
from PIL import Image

from ytdaily.utils.thumbnail import (
    download_thumbnail_bytes,
    is_kitty_or_wezterm,
    is_iterm2,
    to_png_bytes,
    render_kitty_graphics,
    render_iterm2_graphics,
    render_halfblocks_ansi,
    display_terminal_thumbnail,
)


class TestThumbnailUtils(unittest.TestCase):
    def setUp(self):
        # Create a tiny 10x10 RGB test image in memory
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        self.sample_jpeg_bytes = buf.getvalue()

    def test_to_png_bytes(self):
        png = to_png_bytes(self.sample_jpeg_bytes, max_width=50)
        self.assertIsNotNone(png)
        # Verify it can be loaded as PNG
        reloaded = Image.open(io.BytesIO(png))
        self.assertEqual(reloaded.format, "PNG")

    def test_render_kitty_graphics(self):
        png = to_png_bytes(self.sample_jpeg_bytes)
        seq = render_kitty_graphics(png, cols=20)
        self.assertTrue(seq.startswith("\033_G"))
        self.assertIn("a=T,f=100,c=20", seq)
        self.assertTrue(seq.endswith("\033\\\n"))

    def test_render_iterm2_graphics(self):
        png = to_png_bytes(self.sample_jpeg_bytes)
        seq = render_iterm2_graphics(png, cols=20)
        self.assertTrue(seq.startswith("\033]1337;File=inline=1;width=20;"))
        self.assertTrue(seq.endswith("\a\n"))

    def test_render_halfblocks_ansi(self):
        ansi = render_halfblocks_ansi(self.sample_jpeg_bytes, target_cols=10)
        self.assertIn("▀", ansi)
        self.assertIn("\033[38;2;", ansi)

    def test_is_kitty_or_wezterm_detection(self):
        with patch.dict(os.environ, {"TERM_PROGRAM": "WezTerm"}, clear=False):
            self.assertTrue(is_kitty_or_wezterm())

        with patch.dict(os.environ, {"TERM": "xterm-kitty"}, clear=False):
            self.assertTrue(is_kitty_or_wezterm())

        with patch.dict(os.environ, {"KITTY_PID": "1234"}, clear=False):
            self.assertTrue(is_kitty_or_wezterm())

        with patch.dict(os.environ, {"TERM": "xterm"}, clear=True):
            self.assertFalse(is_kitty_or_wezterm())

    def test_is_iterm2_detection(self):
        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}, clear=False):
            self.assertTrue(is_iterm2())

    def test_download_thumbnail_invalid_url(self):
        self.assertIsNone(download_thumbnail_bytes(""))
        self.assertIsNone(download_thumbnail_bytes("ftp://invalid"))
        self.assertIsNone(download_thumbnail_bytes("not_a_url"))


if __name__ == "__main__":
    unittest.main()
