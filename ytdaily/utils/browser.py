"""
Browser detection and cookie support for yt-dlp.
"""

import os
import shutil
import sys
from pathlib import Path
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
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        roaming = Path(os.environ.get("APPDATA", ""))
        profiles = {
            "brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
            "chrome": local / "Google" / "Chrome" / "User Data",
            "chromium": local / "Chromium" / "User Data",
            "firefox": roaming / "Mozilla" / "Firefox" / "Profiles",
            "edge": local / "Microsoft" / "Edge" / "User Data",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "vivaldi": local / "Vivaldi" / "User Data",
        }
        for browser, profile in profiles.items():
            if profile.exists():
                return browser

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
