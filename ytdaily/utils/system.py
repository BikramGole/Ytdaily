"""
System level checks and disk space information.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict, Any


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required binary dependencies are installed.

    Returns:
        (is_all_present, missing_tools_list)
    """
    tools = [
        ("yt-dlp", ["yt-dlp", "--version"]),
        ("ffmpeg", ["ffmpeg", "-version"]),
        ("ffprobe", ["ffprobe", "-version"]),
    ]
    missing = []
    for tool_name, cmd in tools:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool_name)
    return len(missing) == 0, missing


def get_disk_space_info(path: Path) -> Dict[str, Any]:
    """Retrieve formatted disk space usage for a given directory path."""
    try:
        target = path if path.exists() else path.parent
        usage = shutil.disk_usage(target)
        total_gb = usage.total / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        used_pct = (usage.used / usage.total) * 100 if usage.total > 0 else 0

        return {
            "total_gb": f"{total_gb:.1f} GB",
            "free_gb": f"{free_gb:.1f} GB",
            "used_gb": f"{used_gb:.1f} GB",
            "used_percent": f"{used_pct:.1f}%",
            "free_raw_gb": free_gb,
        }
    except Exception:
        return {
            "total_gb": "Unknown",
            "free_gb": "Unknown",
            "used_gb": "Unknown",
            "used_percent": "Unknown",
            "free_raw_gb": 0.0,
        }
