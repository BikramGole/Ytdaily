"""
Metadata extraction via yt-dlp Python API.
Pure Python, no GUI dependency.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path

from core.models import VideoMetadata, VideoFormat


def extract_metadata(url: str, cookies_browser: str = "auto", cookies_file: str = "") -> Optional[VideoMetadata]:
    """
    Extract video metadata from a URL using yt-dlp.
    Returns VideoMetadata or None on error.
    Raises ValueError with a user-friendly message on known errors.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
        "noplaylist": True,
    }

    _apply_cookie_opts(ydl_opts, cookies_browser, cookies_file)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ValueError("No information returned for this URL.")
            return _info_to_metadata(url, info)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private video" in msg:
            raise ValueError("This video is private.")
        if "Video unavailable" in msg:
            raise ValueError("This video is unavailable.")
        if "age" in msg.lower():
            raise ValueError("This video has age restrictions. Try enabling cookies.")
        if "Sign in" in msg:
            raise ValueError("This video requires sign-in. Enable cookies in Settings.")
        raise ValueError(f"Download error: {msg}")
    except Exception as e:
        raise ValueError(f"Failed to fetch metadata: {e}")


def extract_playlist(url: str, cookies_browser: str = "auto", cookies_file: str = "") -> Dict[str, Any]:
    """
    Extract playlist info (list of entries) without downloading.
    Returns dict with title, channel, entries.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,   # don't fetch full info for each video
        "skip_download": True,
    }
    _apply_cookie_opts(ydl_opts, cookies_browser, cookies_file)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Could not extract playlist information.")

    entries = []
    for i, entry in enumerate(info.get("entries", []) or [], start=1):
        if entry is None:
            continue
        entries.append({
            "index": i,
            "video_id": entry.get("id", ""),
            "url": entry.get("url") or entry.get("webpage_url") or f"https://youtube.com/watch?v={entry.get('id','')}",
            "title": entry.get("title", f"Video {i}"),
            "duration": entry.get("duration") or 0,
        })

    return {
        "title": info.get("title", "Playlist"),
        "channel": info.get("uploader") or info.get("channel") or "",
        "entries": entries,
    }


def _apply_cookie_opts(opts: dict, browser: str, cookies_file: str):
    if cookies_file and Path(cookies_file).exists():
        opts["cookiefile"] = cookies_file
    elif browser and browser != "none":
        if browser == "auto":
            import shutil
            for b in ["brave", "chrome", "chromium", "firefox", "edge", "opera", "vivaldi"]:
                commands = {"brave": ["brave", "brave-browser"], "chrome": ["google-chrome", "chrome"],
                            "chromium": ["chromium", "chromium-browser"], "firefox": ["firefox"],
                            "edge": ["microsoft-edge"], "opera": ["opera"], "vivaldi": ["vivaldi"]}
                for cmd in commands.get(b, [b]):
                    if shutil.which(cmd):
                        opts["cookiesfrombrowser"] = (b,)
                        return
        else:
            opts["cookiesfrombrowser"] = (browser,)


def _info_to_metadata(url: str, info: dict) -> VideoMetadata:
    formats: List[VideoFormat] = []
    for f in info.get("formats") or []:
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        height = f.get("height")
        if height:
            res = f"{height}p"
        elif vcodec == "none":
            res = "audio only"
        else:
            res = f.get("format_note") or f.get("format_id", "?")

        formats.append(VideoFormat(
            format_id=f.get("format_id", ""),
            ext=f.get("ext", ""),
            resolution=res,
            fps=f.get("fps"),
            vcodec=vcodec,
            acodec=acodec,
            filesize=f.get("filesize") or f.get("filesize_approx"),
            tbr=f.get("tbr"),
            note=f.get("format_note", ""),
        ))

    # Sort: video-only desc, then audio-only
    def sort_key(fmt: VideoFormat):
        if fmt.resolution == "audio only":
            return (-1, 0)
        try:
            return (int(fmt.resolution.replace("p", "")), 0)
        except Exception:
            return (0, 0)

    formats.sort(key=sort_key, reverse=True)

    return VideoMetadata(
        url=url,
        video_id=info.get("id", ""),
        title=info.get("title", ""),
        channel=info.get("uploader") or info.get("channel") or "",
        channel_url=info.get("uploader_url") or info.get("channel_url") or "",
        duration=int(info.get("duration") or 0),
        upload_date=info.get("upload_date", ""),
        description=info.get("description", "")[:500],
        thumbnail_url=info.get("thumbnail", ""),
        formats=formats,
        webpage_url=info.get("webpage_url", url),
        is_live=bool(info.get("is_live")),
        view_count=info.get("view_count"),
    )


def build_format_string(quality: str, output_format: str, audio_only: bool) -> str:
    """Build a yt-dlp format selector string from user choices."""
    if audio_only:
        return "bestaudio/best"

    ext_pref = output_format if output_format in ("mp4", "webm", "mkv") else "mp4"

    quality_map = {
        "best": f"bestvideo[ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "2160": f"bestvideo[height<=2160][ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best",
        "1440": f"bestvideo[height<=1440][ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best",
        "1080": f"bestvideo[height<=1080][ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
        "720":  f"bestvideo[height<=720][ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
        "480":  f"bestvideo[height<=480][ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best",
        "360":  f"bestvideo[height<=360][ext={ext_pref}]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best",
    }
    return quality_map.get(quality, quality_map["best"])
