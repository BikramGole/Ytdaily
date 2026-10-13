"""
Download engine wrapping yt-dlp Python API.
Emits structured progress events via a callback.
Pure Python — no GUI dependency.
"""

import threading
import time
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from core.models import DownloadOptions, DownloadStatus
from core.metadata import build_format_string, _apply_cookie_opts
from storage import database


ProgressCallback = Callable[[Dict[str, Any]], None]


class DownloadEngine:
    """
    Wraps yt-dlp for a single download item.
    Runs in a thread. Reports structured events via callback.
    """

    def __init__(self, item_id: int, options: DownloadOptions, callback: ProgressCallback):
        self.item_id = item_id
        self.options = options
        self.callback = callback
        self._cancelled = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._history_id: Optional[int] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancelled.set()

    def _run(self):
        import yt_dlp

        opts = self.options
        fmt = build_format_string(opts.quality, opts.output_format, opts.audio_only)

        output_dir = Path(opts.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if opts.audio_only:
            outtmpl = str(output_dir / "%(title)s.%(ext)s")
        else:
            outtmpl = str(output_dir / "%(title)s [%(height)sp].%(ext)s")

        postprocessors = []
        merge_fmt = opts.output_format if opts.output_format in ("mp4", "mkv", "webm") else "mp4"

        if opts.audio_only:
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": opts.output_format if opts.output_format in ("mp3", "m4a", "aac", "flac", "wav") else "m4a",
                "preferredquality": "0",
            })
        else:
            postprocessors.append({
                "key": "FFmpegVideoConvertor",
                "preferedformat": merge_fmt,
            })

        if opts.embed_subs and opts.sub_lang:
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})

        ydl_opts: Dict[str, Any] = {
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": merge_fmt,
            "postprocessors": postprocessors,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
            "noplaylist": True,
            "retries": 3,
            "fragment_retries": 5,
            "ignoreerrors": False,
        }

        if opts.embed_subs and opts.sub_lang:
            ydl_opts["writesubtitles"] = True
            ydl_opts["subtitleslangs"] = [opts.sub_lang]

        # Custom args as string (naive split, for advanced users)
        if opts.custom_args:
            pass  # yt-dlp Python API doesn't take raw CLI args

        from storage.database import get_setting
        browser = get_setting("browser")
        cookies_file = get_setting("cookies_file")
        _apply_cookie_opts(ydl_opts, browser, cookies_file)

        ffmpeg_path = get_setting("ffmpeg_path")
        if ffmpeg_path and Path(ffmpeg_path).exists():
            ydl_opts["ffmpeg_location"] = ffmpeg_path

        proxy = get_setting("proxy")
        if proxy:
            ydl_opts["proxy"] = proxy

        self._emit("preparing", {})

        # Insert history record as "pending"
        self._history_id = database.add_history(
            video_id=opts.video_id,
            url=opts.url,
            title=opts.title or opts.url,
            channel=opts.channel,
            file_path="",
            output_format=opts.output_format,
            quality=opts.quality,
            status="downloading",
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([opts.url])

            if self._cancelled.is_set():
                self._emit("cancelled", {})
                if self._history_id:
                    database.update_history_status(self._history_id, "cancelled")
            else:
                self._emit("completed", {"filename": self._last_filename})
                if self._history_id:
                    database.update_history_status(
                        self._history_id, "completed",
                        file_path=self._last_filename
                    )

        except Exception as e:
            if self._cancelled.is_set():
                self._emit("cancelled", {})
                if self._history_id:
                    database.update_history_status(self._history_id, "cancelled")
            else:
                self._emit("failed", {"error": str(e)})
                if self._history_id:
                    database.update_history_status(
                        self._history_id, "failed", error_msg=str(e)
                    )

    _last_filename: str = ""

    def _progress_hook(self, d: dict):
        if self._cancelled.is_set():
            raise yt_dlp_cancelled()

        status = d.get("status")
        if status == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            speed = d.get("speed")
            eta = d.get("eta")
            pct = 0.0
            if total and total > 0:
                pct = downloaded / total * 100
            self._emit("progress", {
                "progress": pct,
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "speed": speed,
                "eta": eta,
                "filename": d.get("filename", ""),
            })
        elif status == "finished":
            self._last_filename = d.get("filename", "")
            self._emit("processing", {"filename": self._last_filename})

    def _emit(self, event: str, data: dict):
        try:
            self.callback({"item_id": self.item_id, "event": event, **data})
        except Exception:
            pass


class yt_dlp_cancelled(Exception):
    pass
