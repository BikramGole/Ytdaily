"""
Configuration dataclass and validation for Ytdaily.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Dict, Any
from ytdaily.utils.browser import detect_browser, SUPPORTED_BROWSERS
from ytdaily.utils.cache import DirectoryDurationCache

SUPPORTED_RESOLUTIONS: Tuple[str, ...] = ("144", "240", "360", "480", "720", "1080", "1440", "2160")


@dataclass
class Config:
    """Application configuration settings."""

    # Base directories (now configurable in settings)
    base_video_dir: Path = field(default_factory=lambda: Path.home() / "Videos" / "YT_feed")
    base_audio_dir: Path = field(default_factory=lambda: Path.home() / "Music" / "YT_music")
    base_playlist_dir: Path = field(default_factory=lambda: Path.home() / "Videos" / "YT_playlist")
    base_podcast_dir: Path = field(default_factory=lambda: Path.home() / "Music" / "YT_podcasts")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".YT_log")

    # Download settings
    max_resolution: str = "720"
    output_format: str = "mp4"
    download_timeout: int = 1800
    query_timeout: int = 60
    max_retries: int = 2
    retry_delay: int = 3
    max_parallel_downloads: int = 3

    # Log settings
    max_log_files: int = 10
    max_log_size: int = 5 * 1024 * 1024

    # Resume settings
    resume_cache_days: int = 7

    # Channel scan settings
    ask_initial_videos: bool = True
    initial_videos_per_channel: int = 5
    max_videos_per_channel: int = 100

    # Retention & filtering
    cleanup_days: int = 60
    filter_shorts: bool = True
    ask_video_limit_per_channel: bool = False
    gap_check_limit: int = 10
    browser: str = "auto"

    def __post_init__(self):
        """Create base directories and initialize derived paths (defined once)."""
        self.base_video_dir.mkdir(parents=True, exist_ok=True)
        self.base_audio_dir.mkdir(parents=True, exist_ok=True)
        self.base_playlist_dir.mkdir(parents=True, exist_ok=True)
        self.base_podcast_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.download_log_path = self.log_dir / "Download.json"
        self.duration_cache = DirectoryDurationCache(self.log_dir / "directory_durations.json")
        self.config_path = self.log_dir / "config.json"
        self.last_download_path = self.log_dir / "last_download.json"
        self.app_log_path = self.log_dir / "YT_feed.log"
        self.resume_state_path = self.log_dir / "resume_state.json"
        self.channel_history_path = self.log_dir / "channel_history.json"

    @property
    def current_video_dir(self) -> Path:
        """Get the current video directory."""
        return self.base_video_dir

    @property
    def current_audio_dir(self) -> Path:
        """Get the current audio directory."""
        return self.base_audio_dir

    @property
    def current_playlist_dir(self) -> Path:
        """Get the current playlist directory."""
        return self.base_playlist_dir

    @property
    def current_podcast_dir(self) -> Path:
        """Get the current podcast directory."""
        return self.base_podcast_dir

    def get_cookie_args(self) -> List[str]:
        """Return yt-dlp cookie arguments based on browser setting."""
        browser = self.browser
        if browser == "auto":
            browser = detect_browser()
        if browser and browser != "none":
            return ["--cookies-from-browser", browser]
        return []

    def validate(self) -> List[str]:
        """Validate configuration values and return a list of warnings or errors found."""
        issues = []
        if self.max_resolution not in SUPPORTED_RESOLUTIONS:
            issues.append(f"Invalid max_resolution '{self.max_resolution}'. Falling back to 720.")
            self.max_resolution = "720"

        if not (1 <= self.max_parallel_downloads <= 10):
            issues.append(f"Invalid max_parallel_downloads {self.max_parallel_downloads}. Resetting to 3.")
            self.max_parallel_downloads = 3

        if not (1 <= self.resume_cache_days <= 365):
            issues.append(f"Invalid resume_cache_days {self.resume_cache_days}. Resetting to 7.")
            self.resume_cache_days = 7

        if not (1 <= self.cleanup_days <= 3650):
            issues.append(f"Invalid cleanup_days {self.cleanup_days}. Resetting to 60.")
            self.cleanup_days = 60

        if not (0 <= self.initial_videos_per_channel <= self.max_videos_per_channel):
            issues.append(f"Invalid initial_videos_per_channel {self.initial_videos_per_channel}. Resetting to 5.")
            self.initial_videos_per_channel = 5

        valid_browsers = ["auto", "none"] + list(SUPPORTED_BROWSERS)
        if self.browser not in valid_browsers:
            issues.append(f"Invalid browser '{self.browser}'. Resetting to 'auto'.")
            self.browser = "auto"

        return issues
