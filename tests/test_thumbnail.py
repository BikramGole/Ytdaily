"""
Unit tests for terminal and GUI thumbnail rendering utilities.
"""

import io
import os
import unittest
from unittest.mock import patch
from PIL import Image

from ytdaily.utils.thumbnail import (
    calculate_terminal_dimensions,
    download_thumbnail_bytes,
    is_kitty,
    is_wezterm,
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

    def test_calculate_terminal_dimensions(self):
        # 16:9 Landscape
        cols, rows = calculate_terminal_dimensions(1920, 1080, term_cols=80, term_lines=24)
        self.assertLessEqual(rows, 11)
        self.assertGreater(cols, 25)
        # Visual ratio = (cols * 0.5) / rows should be close to 1.78
        self.assertAlmostEqual((cols * 0.5) / rows, 1.78, delta=0.15)

        # 9:16 Portrait
        cols_p, rows_p = calculate_terminal_dimensions(720, 1280, term_cols=80, term_lines=24)
        self.assertLessEqual(rows_p, 11)
        self.assertLess(cols_p, 20)
        # Visual ratio = (cols * 0.5) / rows should be close to 0.56
        self.assertAlmostEqual((cols_p * 0.5) / rows_p, 0.56, delta=0.15)

        # 1:1 Square
        cols_s, rows_s = calculate_terminal_dimensions(1000, 1000, term_cols=80, term_lines=24)
        self.assertAlmostEqual((cols_s * 0.5) / rows_s, 1.0, delta=0.1)

    def test_to_png_bytes(self):
        png = to_png_bytes(self.sample_jpeg_bytes, max_width=50)
        self.assertIsNotNone(png)
        reloaded = Image.open(io.BytesIO(png))
        self.assertEqual(reloaded.format, "PNG")

    def test_render_kitty_graphics(self):
        png = to_png_bytes(self.sample_jpeg_bytes)
        seq = render_kitty_graphics(png, cols=20, rows=10)
        self.assertIn("\033_G", seq)
        self.assertIn("c=20,r=10", seq)
        self.assertTrue(seq.endswith("\033\\\n"))

    def test_render_iterm2_graphics(self):
        png = to_png_bytes(self.sample_jpeg_bytes)
        seq = render_iterm2_graphics(png, cols=20, rows=10)
        self.assertIn("\033]1337;File=inline=1;width=20;height=10;preserveAspectRatio=1:", seq)
        self.assertTrue(seq.endswith("\a\n"))

    def test_render_halfblocks_ansi(self):
        ansi = render_halfblocks_ansi(self.sample_jpeg_bytes, cols=10, rows=5)
        self.assertIn("▀", ansi)
        self.assertIn("\033[38;2;", ansi)
        # Should render 5 lines of text
        self.assertEqual(len(ansi.strip().splitlines()), 5)

    def test_is_wezterm_detection(self):
        with patch.dict(os.environ, {"TERM_PROGRAM": "WezTerm"}, clear=False):
            self.assertTrue(is_wezterm())

        with patch.dict(os.environ, {"WEZTERM_PANE": "0"}, clear=False):
            self.assertTrue(is_wezterm())

        with patch.dict(os.environ, {"TERM": "xterm"}, clear=True):
            self.assertFalse(is_wezterm())

    def test_is_kitty_detection(self):
        with patch.dict(os.environ, {"TERM": "xterm-kitty"}, clear=False):
            self.assertTrue(is_kitty())

        with patch.dict(os.environ, {"KITTY_PID": "1234"}, clear=False):
            self.assertTrue(is_kitty())

        with patch.dict(os.environ, {"TERM": "xterm"}, clear=True):
            self.assertFalse(is_kitty())

    def test_is_iterm2_detection(self):
        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}, clear=False):
            self.assertTrue(is_iterm2())

    def test_download_thumbnail_invalid_url(self):
        self.assertIsNone(download_thumbnail_bytes(""))
        self.assertIsNone(download_thumbnail_bytes("ftp://invalid"))
        self.assertIsNone(download_thumbnail_bytes("not_a_url"))


if __name__ == "__main__":
    unittest.main()
