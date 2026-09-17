"""
Duration cache and directory duration calculation.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

# Single definition of duration regex for matching duration suffixes
DURATION_REGEX = re.compile(
    r'\s*-\s*\d+(\.\d+)?(?:hr|min|sec|h|m|s)(?:\s*\d+(\.\d+)?(?:min|sec|m|s))?$',
    re.IGNORECASE,
)


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "Unknown"
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    except (TypeError, ValueError):
        return "Unknown"


def format_duration_short(seconds: Optional[float]) -> str:
    """Format duration in seconds to short format like '3hr 45min' or '26sec' with rounding."""
    if seconds is None or seconds < 0:
        return "Unknown"
    try:
        seconds_rounded = round(float(seconds))
        hours = seconds_rounded // 3600
        minutes = (seconds_rounded % 3600) // 60
        remaining_seconds = seconds_rounded % 60

        if hours > 0:
            if minutes > 0:
                return f"{hours}hr {minutes}min"
            return f"{hours}hr"
        if minutes > 0:
            if remaining_seconds > 0:
                return f"{minutes}min {remaining_seconds}sec"
            return f"{minutes}min"
        return f"{remaining_seconds}sec"
    except (TypeError, ValueError):
        return "Unknown"


class DirectoryDurationCache:
    """Cache for file media durations to avoid repeated ffprobe calls."""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()
        self._dirty = False

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self):
        if self._dirty:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f)
                self._dirty = False
            except Exception:
                pass

    def get(self, file_path: Path) -> Optional[float]:
        key = str(file_path)
        if key in self.cache:
            entry = self.cache[key]
            try:
                stat = file_path.stat()
                if entry.get("mtime") == stat.st_mtime and entry.get("size") == stat.st_size:
                    return entry.get("duration")
            except (FileNotFoundError, OSError):
                pass
        return None

    def set(self, file_path: Path, duration: float):
        try:
            stat = file_path.stat()
            self.cache[str(file_path)] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "duration": duration,
            }
            self._dirty = True
        except (FileNotFoundError, OSError):
            pass


def calculate_directory_duration(directory: Path, cache: Optional[DirectoryDurationCache] = None) -> Tuple[float, str, str]:
    """Calculate total duration of all media files in a directory.

    Returns:
        (total_seconds, duration_short_string, file_info_string)
    """
    try:
        media_extensions = [
            "*.mp3", "*.wav", "*.flac", "*.aac", "*.ogg", "*.m4a",
            "*.mp4", "*.mkv", "*.avi", "*.mov", "*.flv", "*.webm",
        ]

        total_seconds = 0.0
        file_count = 0

        for extension in media_extensions:
            for file_path in directory.rglob(extension):
                # Check cache first
                if cache is not None:
                    cached_duration = cache.get(file_path)
                    if cached_duration is not None:
                        total_seconds += cached_duration
                        file_count += 1
                        continue

                try:
                    cmd = [
                        "ffprobe", "-v", "quiet", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", str(file_path),
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
                    duration_str = result.stdout.strip()
                    if duration_str:
                        duration = float(duration_str)
                        if cache is not None:
                            cache.set(file_path, duration)
                        total_seconds += duration
                        file_count += 1
                except (subprocess.CalledProcessError, ValueError, FileNotFoundError, subprocess.TimeoutExpired):
                    continue

        if cache is not None:
            cache.save()

        if file_count == 0:
            return 0.0, "0sec", "No media files"

        return total_seconds, format_duration_short(total_seconds), f"{file_count} files"

    except Exception:
        return 0.0, "Error", "Error"


def rename_directory_with_duration(directory: Path, base_name: str, cache: Optional[DirectoryDurationCache] = None) -> Tuple[Path, float, str]:
    """Rename directory to include total duration.

    Returns:
        (new_path, total_seconds, duration_short)
    """
    try:
        if not directory.exists():
            return directory, 0.0, "0sec"

        total_seconds, duration_short, _ = calculate_directory_duration(directory, cache)

        clean_base = DURATION_REGEX.sub("", base_name).strip()
        clean_base = re.sub(r'\s*-\s*\d+[hmr]\s*\d*[ms]?in?$', '', clean_base)
        clean_base = re.sub(r'\s*-\s*\d+sec$', '', clean_base)
        clean_base = re.sub(r'\s*-\s*\d+\.\d+sec$', '', clean_base)

        if total_seconds > 0:
            new_name = f"{clean_base} -{duration_short}"
        else:
            new_name = clean_base

        new_path = directory.parent / new_name

        if new_path != directory and not new_path.exists():
            try:
                directory.rename(new_path)
                return new_path, total_seconds, duration_short
            except OSError:
                return directory, total_seconds, duration_short
        elif new_path.exists() and new_path != directory:
            return new_path, total_seconds, duration_short

        return directory, total_seconds, duration_short

    except Exception:
        return directory, 0.0, "Error"
