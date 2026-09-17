"""
Browser detection and cookie support for yt-dlp.
"""

import shutil
from typing import Tuple

SUPPORTED_BROWSERS: Tuple[str, ...] = (
    "brave",
    "chrome",
    "chromium",
    "firefox",
    "edge",
    "opera",
    "vivaldi",
    "safari",
)


def detect_browser() -> str:
    """Auto-detect the first available browser for cookie extraction."""
    browser_commands = {
        "brave": ["brave", "brave-browser"],
        "chrome": ["google-chrome", "google-chrome-stable"],
        "chromium": ["chromium", "chromium-browser"],
        "firefox": ["firefox"],
        "edge": ["microsoft-edge", "microsoft-edge-stable"],
        "opera": ["opera"],
        "vivaldi": ["vivaldi", "vivaldi-stable"],
    }
    for browser_name, commands in browser_commands.items():
        for cmd in commands:
            if shutil.which(cmd):
                return browser_name
    return "none"
