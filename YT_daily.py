#!/usr/bin/env python3
"""
YouTube Feed Downloader - Modular Entry Point.
Maintains backward compatibility with install.sh, systemd services, and aliases.
"""

import sys
from pathlib import Path

# Ensure ytdaily package can be found if running directly from script directory
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from ytdaily.config import Config
from ytdaily.ui.app import YtdailyApp, YtdailyApp as YouTubeFeedDownloader
from ytdaily.main import main

if __name__ == "__main__":
    main()
