"""
SponsorBlock configuration and yt-dlp command generation.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
from ytdaily.config import Config

SPONSORBLOCK_CATEGORIES = "sponsor,intro,outro,selfpromo,preview,interaction"

# Emoji, variation selectors, ZWJ, keycaps, and misc-symbol blocks that only
# decorate titles; stripped from filenames via --replace-in-metadata.
EMOJI_PATTERN = (
    "[\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\U0001F000-\U0001FAFF\uFE0F\u200D\u20E3]"
)

# Bases of the Mathematical Alphanumeric Symbols sub-blocks (bold, italic,
# fraktur, sans, monospace, ... styles of A-Z, a-z, and 0-9). Each such char
# costs 3-4 UTF-8 bytes, so long styled titles overflow the 255-byte
# filesystem filename limit (ERROR: [Errno 36] File name too long) before
# yt-dlp's char-counting --trim-filenames can help. Transliterating them to
# ASCII keeps the full title readable and byte-safe.
_MATH_LATIN_BASES = [
    0x1D400, 0x1D434, 0x1D468, 0x1D49C, 0x1D4D0, 0x1D504, 0x1D538,
    0x1D56C, 0x1D5A0, 0x1D5D4, 0x1D608, 0x1D63C, 0x1D670,
]
_MATH_DIGIT_BASES = [0x1D7CE, 0x1D7D8, 0x1D7E2, 0x1D7EC, 0x1D7F6]


def _trim_file_name_limit(output_dir: Path) -> int:
    """--trim-filenames value that cannot overflow the 255-byte name cap.

    yt-dlp trims the rendered filename's no-extension part -- which includes
    the output directory -- to that many characters, so the limit must leave
    room for the directory. Characters surviving the transliteration and emoji
    stripping (fullwidth punctuation, CJK, ...) still cost up to 3 UTF-8 bytes
    each, so budget 3 bytes per title character plus room for extension and
    suffixes.
    """
    dir_str = str(output_dir)
    dir_bytes = len(dir_str.encode())
    stem_chars = max((255 - dir_bytes - 9) // 3, 20)
    return min(len(dir_str) + stem_chars, 240)


def _filename_safety_args(url: str, output_dir: Path) -> List[str]:
    """yt-dlp args that keep output filenames short and readable for YouTube.

    - Transliterate Mathematical Alphanumeric Symbols to ASCII letters/digits.
    - Strip emoji and variation selectors (decorative, 3-4 bytes each).
    - Trim overly long titles as a backstop, sized against the output
      directory so yt-dlp's char-counting trim cannot overflow the 255-byte
      filesystem filename limit (ERROR: [Errno 36] File name too long).

    Non-YouTube URLs get their own naming rules and are skipped.
    """
    if not is_youtube_url(url):
        return []

    args: List[str] = ["--trim-filenames", str(_trim_file_name_limit(output_dir))]
    for base in _MATH_LATIN_BASES:
        for i in range(26):
            args += ["--replace-in-metadata", "title", chr(base + i), chr(ord("A") + i)]
            args += ["--replace-in-metadata", "title", chr(base + 26 + i), chr(ord("a") + i)]
    for base in _MATH_DIGIT_BASES:
        for i in range(10):
            args += ["--replace-in-metadata", "title", chr(base + i), chr(ord("0") + i)]
    args += ["--replace-in-metadata", "title", EMOJI_PATTERN, ""]
    return args


def is_youtube_url(url: str) -> bool:
    """Check if a URL belongs to YouTube."""
    return bool(re.search(r'(?:youtube\.com|youtu\.be)', url, re.IGNORECASE))


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
        "-f", f"bestvideo[height<={config.max_resolution}]+bestaudio/best[height<={config.max_resolution}]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        *config.get_cookie_args_for_url(video_url),
        *config.get_network_args(),
        "--no-cache-dir",
        "--no-part",
        "--no-mtime",
    ]

    if is_youtube_url(video_url):
        cmd.extend(["--sponsorblock-remove", SPONSORBLOCK_CATEGORIES])
        cmd.extend(_filename_safety_args(video_url, output_dir))
    else:
        cmd.extend(["--parse-metadata", r"description:(?P<title>[^\n]+)",
                    "--trim-filenames", str(_trim_file_name_limit(output_dir))])

    cmd.extend([
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
    ])

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
        *config.get_cookie_args_for_url(video_url),
        *config.get_network_args(),
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

    if not is_youtube_url(video_url):
        cmd.extend(["--parse-metadata", r"description:(?P<title>[^\n]+)",
                    "--trim-filenames", str(_trim_file_name_limit(output_dir))])
    else:
        cmd.extend(_filename_safety_args(video_url, output_dir))

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
    playlist_items: Optional[List[int]] = None,
) -> Tuple[List[str], Path]:
    """Build the yt-dlp command for all or selected playlist entries."""
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
            *config.get_cookie_args_for_url(playlist_url),
            *config.get_network_args(),
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
        if not is_youtube_url(playlist_url):
            cmd.extend(["--parse-metadata", r"description:(?P<title>[^\n]+)",
                        "--trim-filenames", str(_trim_file_name_limit(playlist_dir))])
        else:
            cmd.extend(_filename_safety_args(playlist_url, playlist_dir))
    else:
        playlist_dir = config.current_playlist_dir / safe_name
        output_template = str(playlist_dir / "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", f"bestvideo[height<={config.max_resolution}]+bestaudio/best[height<={config.max_resolution}]/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            *config.get_cookie_args_for_url(playlist_url),
            *config.get_network_args(),
            "--no-cache-dir",
            "--no-part",
            "--no-mtime",
        ]
        if is_youtube_url(playlist_url):
            cmd.extend(["--sponsorblock-remove", SPONSORBLOCK_CATEGORIES])
            cmd.extend(_filename_safety_args(playlist_url, playlist_dir))
        else:
            cmd.extend(["--parse-metadata", r"description:(?P<title>[^\n]+)",
                        "--trim-filenames", str(_trim_file_name_limit(playlist_dir))])
        cmd.extend([
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
        ])

    # YouTube tab extraction can abort when YouTube serves a bot-check page
    # instead of the playlist webpage; skipping the auth pre-check keeps
    # public playlist downloads working.
    if is_youtube_url(playlist_url):
        cmd.extend(["--extractor-args", "youtubetab:skip=authcheck"])

    if resume:
        cmd.append("--continue")
    else:
        cmd.append("--no-continue")

    if playlist_items is not None:
        selected_items = sorted({item for item in playlist_items if item > 0})
        if not selected_items:
            raise ValueError("At least one playlist item must be selected")
        cmd.extend(["--playlist-items", ",".join(map(str, selected_items))])

    cmd.append(playlist_url)
    playlist_dir.mkdir(parents=True, exist_ok=True)
    return cmd, playlist_dir
