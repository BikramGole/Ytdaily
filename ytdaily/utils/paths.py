"""Operating-system aware locations used by Ytdaily."""

import os
import sys
from pathlib import Path


APP_NAME = "Ytdaily"


def application_data_dir() -> Path:
    """Return the writable per-user data directory used for state and logs."""
    if sys.platform == "win32":
        fallback = Path.home() / "AppData" / "Local"
        return Path(os.environ.get("LOCALAPPDATA", fallback)) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    # Preserve the established Linux location, including current user data.
    return Path.home() / ".YT_log"
