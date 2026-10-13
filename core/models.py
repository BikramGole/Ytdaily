"""
Core data models for YTDaily.
Pure Python — no GUI dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class DownloadStatus(Enum):
    QUEUED      = "Queued"
    PREPARING   = "Preparing"
    DOWNLOADING = "Downloading"
    PROCESSING  = "Processing"
    PAUSED      = "Paused"
    COMPLETED   = "Completed"
    FAILED      = "Failed"
    CANCELLED   = "Cancelled"


@dataclass
class VideoFormat:
    format_id: str
    ext: str
    resolution: str          # e.g. "1080p", "720p", "audio only"
    fps: Optional[float]
    vcodec: str
    acodec: str
    filesize: Optional[int]  # bytes, may be None
    tbr: Optional[float]     # total bitrate
    note: str = ""

    def display(self) -> str:
        size_str = ""
        if self.filesize:
            mb = self.filesize / 1_048_576
            size_str = f" ~{mb:.0f}MB"
        fps_str = f" {self.fps:.0f}fps" if self.fps and self.fps > 1 else ""
        return f"{self.resolution}{fps_str} [{self.ext}]{size_str}"


@dataclass
class VideoMetadata:
    url: str
    video_id: str
    title: str
    channel: str
    channel_url: str
    duration: int            # seconds
    upload_date: str         # YYYYMMDD string
    description: str
    thumbnail_url: str
    formats: List[VideoFormat] = field(default_factory=list)
    webpage_url: str = ""
    is_live: bool = False
    view_count: Optional[int] = None

    def duration_str(self) -> str:
        s = self.duration
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"

    def upload_date_str(self) -> str:
        try:
            d = datetime.strptime(self.upload_date, "%Y%m%d")
            return d.strftime("%b %d, %Y")
        except Exception:
            return self.upload_date


@dataclass
class DownloadOptions:
    url: str
    title: str = ""
    format_id: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    output_format: str = "mp4"      # mp4, mkv, webm, mp3, m4a
    quality: str = "best"           # best, 2160, 1440, 1080, 720, 480, 360
    audio_only: bool = False
    embed_subs: bool = False
    sub_lang: str = ""
    output_dir: Path = field(default_factory=Path.cwd)
    custom_args: str = ""
    video_id: str = ""
    channel: str = ""
    thumbnail_url: str = ""
    duration: int = 0


@dataclass
class DownloadItem:
    id: int                          # unique row id from DB
    options: DownloadOptions
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0            # 0-100
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None    # bytes/sec
    eta: Optional[float] = None      # seconds
    filename: str = ""
    error_msg: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    thumbnail_data: Optional[bytes] = None  # cached thumbnail pixmap bytes

    @property
    def title(self) -> str:
        return self.options.title or self.options.url

    @property
    def channel(self) -> str:
        return self.options.channel

    @property
    def url(self) -> str:
        return self.options.url


@dataclass
class HistoryEntry:
    id: int
    video_id: str
    url: str
    title: str
    channel: str
    downloaded_at: datetime
    file_path: str
    output_format: str
    quality: str
    status: str      # "completed" or "failed"
    error_msg: str = ""


@dataclass
class ChannelSubscription:
    id: int
    name: str
    url: str
    channel_id: str
    last_checked: Optional[datetime]
    auto_download: bool = False


@dataclass
class PlaylistItem:
    index: int
    video_id: str
    url: str
    title: str
    duration: int
    selected: bool = True
