"""
SponsorBlock configuration and yt-dlp command generation.
"""

import re
from pathlib import Path
from typing import List, Tuple
from ytdaily.config import Config

SPONSORBLOCK_CATEGORIES = "sponsor,intro,outro,selfpromo,preview,interaction"


def build_video_download_command(
    config: Config,
    video_url: str,
    output_dir: Path,
    skip_subs: bool = False,
    resume: bool = False,
) -> List[str]:
    """Build the yt-dlp command for video downloads."""
    output_template = str(output_dir / "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", f"bestvideo[height<={config.max_resolution}]+bestaudio/best[height<={config.max_resolution}]",
        "--merge-output-format", "mp4",
        *config.get_cookie_args(),
        "--no-cache-dir",
        "--no-part",
        "--no-mtime",
        "--sponsorblock-remove", SPONSORBLOCK_CATEGORIES,
        "--embed-chapters",
        "--embed-metadata",
        "--no-embed-thumbnail",
        "--no-playlist",
        "--output", output_template,
        "--newline",
        "--no-warnings",
        "--progress",
        "--retries", "10",
        "--fragment-retries", "10",
        "--file-access-retries", "5",
        "--socket-timeout", "30",
    ]

    if resume:
        cmd.append("--continue")
    else:
        cmd.append("--no-continue")

    if not skip_subs:
        cmd.extend([
            "--write-auto-sub",
            "--write-sub",
            "--sub-langs", "en",
            "--convert-subs", "srt",
            "--embed-subs",
        ])

    cmd.append(video_url)
    return cmd


def build_audio_download_command(
    config: Config,
    video_url: str,
    output_dir: Path,
    resume: bool = False,
) -> List[str]:
    """Build the yt-dlp command for 320kbps MP3 audio downloads."""
    output_template = str(output_dir / "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "320K",
        *config.get_cookie_args(),
        "--no-cache-dir",
        "--no-part",
        "--no-mtime",
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-playlist",
        "--output", output_template,
        "--newline",
        "--no-warnings",
        "--progress",
        "--retries", "10",
        "--fragment-retries", "10",
        "--file-access-retries", "5",
        "--socket-timeout", "30",
    ]

    if resume:
        cmd.append("--continue")
    else:
        cmd.append("--no-continue")

    cmd.append(video_url)
    return cmd


def build_playlist_download_command(
    config: Config,
    playlist_url: str,
    playlist_name: str,
    download_type: str = "video",
    resume: bool = False,
) -> Tuple[List[str], Path]:
    """Build the yt-dlp command for downloading entire playlists."""
    safe_name = re.sub(r'[<>:"/\\|?*]', '', playlist_name)

    if download_type == "audio":
        playlist_dir = config.current_podcast_dir / safe_name
        output_template = str(playlist_dir / "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "320K",
            *config.get_cookie_args(),
            "--no-cache-dir",
            "--no-part",
            "--no-mtime",
            "--embed-metadata",
            "--embed-thumbnail",
            "--yes-playlist",
            "--output", output_template,
            "--newline",
            "--no-warnings",
            "--progress",
            "--retries", "10",
            "--fragment-retries", "10",
            "--file-access-retries", "5",
            "--socket-timeout", "30",
        ]
    else:
        playlist_dir = config.current_playlist_dir / safe_name
        output_template = str(playlist_dir / "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", f"bestvideo[height<={config.max_resolution}]+bestaudio/best[height<={config.max_resolution}]",
            "--merge-output-format", "mp4",
            *config.get_cookie_args(),
            "--no-cache-dir",
            "--no-part",
            "--no-mtime",
            "--sponsorblock-remove", SPONSORBLOCK_CATEGORIES,
            "--embed-metadata",
            "--embed-chapters",
            "--yes-playlist",
            "--output", output_template,
            "--newline",
            "--no-warnings",
            "--progress",
            "--retries", "10",
            "--fragment-retries", "10",
            "--file-access-retries", "5",
            "--socket-timeout", "30",
        ]

    if resume:
        cmd.append("--continue")
    else:
        cmd.append("--no-continue")

    cmd.append(playlist_url)
    playlist_dir.mkdir(parents=True, exist_ok=True)
    return cmd, playlist_dir
