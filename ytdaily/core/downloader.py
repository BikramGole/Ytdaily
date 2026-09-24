"""
Download orchestration, parallel execution, and progress management.
"""

import glob
import logging
import os
import queue
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, Iterator, List, Optional, Tuple

from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.table import Table

from ytdaily.config import Config
from ytdaily.core.scanner import Scanner
from ytdaily.core.sponsorblock import (
    build_video_download_command,
    build_audio_download_command,
    build_playlist_download_command,
)
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.widgets.progress import (
    create_single_progress,
    create_playlist_progress,
    create_parallel_progress,
)
from ytdaily.utils.notifications import send_notification


ProgressCallback = Callable[[Dict[str, Any]], None]


class Downloader:
    """Orchestrates single, playlist, and parallel downloads."""

    def __init__(
        self,
        config: Config,
        state: StateManager,
        scanner: Scanner,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config
        self.state = state
        self.scanner = scanner
        self.logger = logger or logging.getLogger("ytdaily")

    def parse_progress(self, line: str) -> Optional[Dict[str, str]]:
        """Parse yt-dlp progress output."""
        progress_match = re.search(
            r'\[download\]\s+(\d+\.?\d*)%\s+of\s+~?\s*(\d+\.?\d*)(\w+)\s+at\s+(\d+\.?\d*)(\w+)/s\s+ETA\s+(\d+:\d+|\d+)',
            line,
        )
        if progress_match:
            return {
                "type": "download",
                "percent": progress_match.group(1),
                "size": f"{progress_match.group(2)}{progress_match.group(3)}",
                "speed": f"{progress_match.group(4)}{progress_match.group(5)}/s",
                "eta": progress_match.group(6),
            }

        extract_match = re.search(r'\[ExtractAudio\]\s+Destination:\s+(.+)', line)
        if extract_match:
            return {"type": "extract", "file": extract_match.group(1)}

        ffmpeg_match = re.search(r'\[FFmpeg\]\s+Converting\s+.+\s+to\s+.+', line)
        if ffmpeg_match:
            return {"type": "converting"}

        playlist_match = re.search(r'\[download\]\s+Downloading\s+item\s+(\d+)\s+of\s+(\d+)', line)
        if playlist_match:
            return {
                "type": "playlist_progress",
                "current": playlist_match.group(1),
                "total": playlist_match.group(2),
            }

        if "[download] Destination:" in line:
            return {"type": "starting"}

        return None

    def cleanup_old_videos(self) -> int:
        """Delete videos older than configured days from YT_feed directories."""
        cleaned_count = 0
        try:
            cutoff_time = time.time() - (self.config.cleanup_days * 86400)
            videos_dir = self.config.base_video_dir.parent
            yt_feed_dirs = list(videos_dir.glob("YT_feed*"))

            for directory in yt_feed_dirs:
                if directory.is_dir():
                    for file_path in directory.glob("*"):
                        if file_path.is_file():
                            try:
                                if file_path.stat().st_mtime < cutoff_time:
                                    file_path.unlink()
                                    cleaned_count += 1
                                    self.logger.info(f"🧹 Deleted old file: {file_path.name}")
                            except Exception as e:
                                self.logger.warning(f"⚠️ Could not delete {file_path}: {e}")

            if cleaned_count > 0:
                console.print(
                    f"[warning]🧹 Cleaned up {cleaned_count} videos older than {self.config.cleanup_days} days[/warning]"
                )
                send_notification("Cleanup Complete", f"Removed {cleaned_count} old videos")

        except Exception as e:
            self.logger.error(f"❌ Error during video cleanup: {e}")

        return cleaned_count

    def cleanup_empty_directories(self) -> None:
        """Clean up empty YT_feed directories that might have been created."""
        try:
            videos_dir = self.config.base_video_dir.parent
            yt_feed_dirs = list(videos_dir.glob("YT_feed*"))

            for directory in yt_feed_dirs:
                if directory.is_dir():
                    files = list(directory.glob("*"))
                    if len(files) <= 1:
                        if directory != self.config.current_video_dir:
                            try:
                                for file_path in directory.glob("*"):
                                    try:
                                        file_path.unlink()
                                    except Exception:
                                        pass
                                directory.rmdir()
                                self.logger.info(f"🧹 Cleaned up empty directory: {directory}")
                            except Exception as e:
                                self.logger.warning(f"⚠️ Could not remove directory {directory}: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error during directory cleanup: {e}")

    def cleanup_subtitle_files(self, video_title: str) -> None:
        """Clean up temporary subtitle files after embedding."""
        try:
            clean_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()

            subtitle_patterns = [
                f"*{clean_title}*.en.srt",
                f"*{clean_title}*.srt",
                f"*{clean_title}*.vtt",
                f"*{clean_title}*.en.vtt",
                f"*.srt",
                f"*.vtt",
            ]

            files_cleaned = 0
            for pattern in subtitle_patterns:
                full_pattern = os.path.join(self.config.current_video_dir, pattern)
                for file_path in glob.glob(full_pattern):
                    try:
                        if file_path.endswith(('.srt', '.vtt')) and os.path.isfile(file_path):
                            if not file_path.endswith(('.mp4', '.mkv', '.webm', '.mp3', '.m4a')):
                                try:
                                    os.remove(file_path)
                                    self.logger.info(f"🧹 Cleaned up subtitle file: {os.path.basename(file_path)}")
                                    files_cleaned += 1
                                except FileNotFoundError:
                                    pass
                    except OSError as e:
                        self.logger.warning(f"⚠️ Could not remove subtitle file {file_path}: {e}")

            if files_cleaned == 0:
                current_time = time.time()
                for ext in ['.srt', '.vtt']:
                    for file_path in self.config.current_video_dir.glob(f"*{ext}"):
                        try:
                            if file_path.stat().st_mtime > current_time - 3600:
                                os.remove(file_path)
                                self.logger.info(f"🧹 Cleaned up recent subtitle file: {file_path.name}")
                                files_cleaned += 1
                        except OSError as e:
                            self.logger.warning(f"⚠️ Could not remove recent subtitle file {file_path}: {e}")

            self.logger.info(f"🧹 Subtitle cleanup completed: {files_cleaned} files removed")
        except Exception as e:
            self.logger.error(f"❌ Error during subtitle cleanup: {e}")

    def check_existing_download(self, video_info: Dict[str, Any], download_type: str = "video") -> Tuple[bool, int]:
        """Check if download exists and can be resumed. Returns (can_resume, progress_percent)."""
        try:
            video_title = video_info.get("title", "Unknown")
            clean_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)

            if download_type == "video":
                download_dir = self.config.current_video_dir
                file_pattern = f"*{clean_title}*.mp4"
            else:
                download_dir = self.config.current_audio_dir
                file_pattern = f"*{clean_title}*.mp3"

            for file_path in download_dir.glob(file_pattern):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    if file_size > 1024 * 1024:
                        return True, 50
                    return True, 100

            return False, 0
        except Exception as e:
            self.logger.warning(f"⚠️ Error checking existing download: {e}")
            return False, 0

    def download_video(
        self,
        video_info: Dict[str, Any],
        source_name: str,
        is_manual: bool = False,
        progress: Optional[Progress] = None,
        task_id: Optional[TaskID] = None,
        is_audio: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
        show_console: bool = True,
    ) -> Tuple[bool, str]:
        """Download a single video or audio file with Rich progress tracking and error recovery."""
        video_id = video_info["id"]
        video_url = video_info["url"]
        video_title = video_info.get("title", "Unknown")
        duration = video_info.get("duration_formatted", "Unknown")
        download_type = "audio" if is_audio else "video"

        can_resume, current_resume_progress = self.check_existing_download(video_info, download_type)
        resume_state = self.state.get_resume_state(download_type, video_id)

        resume = False
        resume_msg = ""
        if can_resume and current_resume_progress < 100:
            resume_msg = f"[yellow]🔄 Resuming from {current_resume_progress}%[/yellow]"
            resume = True
        elif resume_state and current_resume_progress < 100:
            resume_msg = f"[yellow]🔄 Resuming previous download[/yellow]"
            resume = True

        # If not already running inside an external Progress context, show info Panel
        if not progress and show_console:
            grid = Table.grid(padding=(0, 2))
            grid.add_column(style="bold cyan", justify="right")
            grid.add_column(style="white")
            grid.add_row("Source:", source_name)
            grid.add_row("Title:", video_title)
            grid.add_row("Duration:", duration)
            if resume_msg:
                grid.add_row("Status:", resume_msg)

            console.print(
                Panel(grid, title=f"[bold green]Downloading {download_type.capitalize()}[/bold green]", border_style="green")
            )

        has_subtitles = self.scanner.check_subtitles_available(video_url) if not is_audio else False

        if resume:
            self.state.update_resume_state(download_type, video_id, {
                "url": video_url,
                "title": video_title,
                "source": source_name,
                "progress": current_resume_progress,
                "type": download_type,
            })

        output_dir = self.config.current_audio_dir if is_audio else self.config.current_video_dir

        # Helper to execute download
        def run_attempt(skip_subs: bool, do_resume: bool) -> Tuple[bool, str, str]:
            if is_audio:
                cmd = build_audio_download_command(self.config, video_url, output_dir, resume=do_resume)
            else:
                cmd = build_video_download_command(self.config, video_url, output_dir, skip_subs=skip_subs, resume=do_resume)
            return self._execute_download(
                cmd,
                video_info,
                source_name,
                is_audio=is_audio,
                progress=progress,
                task_id=task_id,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
                show_console=show_console,
            )

        success, vid_id, error_msg = run_attempt(skip_subs=not has_subtitles, do_resume=resume)

        # Retry without subtitles if subtitle 429/error detected
        if not success and has_subtitles and ("subtitles" in error_msg.lower() or "429" in error_msg):
            if not progress and show_console:
                console.print("   [warning]⚠️ Subtitle error detected, retrying without subtitles...[/warning]")
            success, vid_id, error_msg = run_attempt(skip_subs=True, do_resume=resume)

        # Retry clean if HTTP 416 (corrupted cache)
        if not success and "416" in error_msg:
            if not progress and show_console:
                console.print("   [warning]⚠️ Cache error detected (HTTP 416), retrying clean...[/warning]")
            success, vid_id, _ = run_attempt(skip_subs=True, do_resume=False)

        if success:
            if has_subtitles and not is_audio:
                self.cleanup_subtitle_files(video_title)

            if not progress and show_console:
                console.print("   [bold green]✅ Download complete![/bold green]")

            self._save_download_success(video_info, source_name, video_title, is_audio=is_audio)
            self.state.clear_resume_state(download_type, video_id)
            self._emit_progress(progress_callback, {"type": "completed", "video_id": video_id, "title": video_title})
            return True, video_id
        else:
            if not progress and show_console:
                console.print("   [bold red]❌ Download failed[/bold red]")
                if error_msg:
                    console.print(f"   [red]Error: {error_msg[:120]}[/red]")
            self._emit_progress(progress_callback, {
                "type": "failed", "video_id": video_id, "title": video_title, "message": error_msg,
            })
            return False, video_id

    def _execute_download(
        self,
        cmd: List[str],
        video_info: Dict[str, Any],
        source_name: str,
        is_audio: bool = False,
        progress: Optional[Progress] = None,
        task_id: Optional[TaskID] = None,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
        show_console: bool = True,
    ) -> Tuple[bool, str, str]:
        """Execute download command with Rich progress display (no raw ANSI codes)."""
        video_id = video_info["id"]
        video_title = video_info.get("title", "Unknown")
        display_title = (video_title[:45] + "…") if len(video_title) > 45 else video_title

        # If no external progress is passed, create a single Rich Progress widget
        standalone_progress = None
        if progress is None and show_console:
            standalone_progress = create_single_progress()
            standalone_progress.start()
            task_id = standalone_progress.add_task(f"[cyan]{display_title}[/cyan]", total=100, speed="", eta="")
            active_progress = standalone_progress
        else:
            active_progress = progress

        try:
            download_type = "audio" if is_audio else "video"
            self.logger.info(f"🚀 Starting {download_type} download: {source_name} - {video_title}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            stderr_lines = []
            lines = self._read_process_output(process, cancel_event)
            for stream_name, line in lines:
                if stream_name == "stderr":
                    stderr_lines.append(line)

                progress_dict = self.parse_progress(line)
                if progress_dict:
                    progress_dict["video_id"] = video_id
                    progress_dict["title"] = video_title
                    self._emit_progress(progress_callback, progress_dict)
                    if active_progress and task_id is not None:
                        if progress_dict.get("type") == "starting":
                            active_progress.update(task_id, description=f"[yellow]Connecting…[/yellow] {display_title}")
                        elif progress_dict.get("type") == "download" and "percent" in progress_dict:
                            try:
                                percent = float(progress_dict["percent"])
                            except ValueError:
                                percent = 0.0
                            active_progress.update(
                                task_id,
                                completed=percent,
                                description=f"[cyan]{display_title}[/cyan]",
                                speed=progress_dict.get("speed", ""),
                                eta=progress_dict.get("eta", ""),
                                visible=True,
                            )
                        elif progress_dict.get("type") in ("extract", "converting"):
                            active_progress.update(task_id, description=f"[yellow]Processing audio…[/yellow] {display_title}")

            return_code = process.wait()
            error_summary = "".join(stderr_lines[-5:]) if stderr_lines else "Unknown error"

            if return_code == 0:
                if any("ERROR:" in line for line in stderr_lines):
                    return False, video_id, error_summary
                if active_progress and task_id is not None:
                    active_progress.update(task_id, completed=100)
                return True, video_id, ""
            else:
                return False, video_id, error_summary

        except subprocess.TimeoutExpired:
            self.logger.error(f"⏱️ Download timeout for {source_name}")
            return False, video_id, "Download timeout"
        except Exception as e:
            self.logger.error(f"❌ Download error for {source_name}: {e}")
            return False, video_id, str(e)
        finally:
            if standalone_progress is not None:
                standalone_progress.stop()

    @staticmethod
    def _emit_progress(callback: Optional[ProgressCallback], event: Dict[str, Any]) -> None:
        """Invoke a UI callback without allowing UI failures to stop a download."""
        if callback is None:
            return
        try:
            callback(event)
        except Exception:
            logging.getLogger("ytdaily").debug("Progress callback failed", exc_info=True)

    def _read_process_output(
        self,
        process: subprocess.Popen,
        cancel_event: Optional[threading.Event] = None,
    ) -> Iterator[Tuple[str, str]]:
        """Read stdout/stderr concurrently on Linux and Windows.

        Windows ``select`` only accepts sockets, not subprocess pipes. Dedicated
        reader threads work on both platforms and also drain the error stream so
        a noisy downloader cannot deadlock.
        """
        output: "queue.Queue[Tuple[str, str]]" = queue.Queue()

        def reader(stream: Any, name: str) -> None:
            try:
                for line in iter(stream.readline, ""):
                    output.put((name, line))
            finally:
                stream.close()

        readers = [
            threading.Thread(target=reader, args=(process.stdout, "stdout"), daemon=True),
            threading.Thread(target=reader, args=(process.stderr, "stderr"), daemon=True),
        ]
        for thread in readers:
            thread.start()

        started_at = time.monotonic()
        terminated = False
        while process.poll() is None or not output.empty():
            if cancel_event is not None and cancel_event.is_set() and not terminated:
                process.terminate()
                terminated = True
            elif time.monotonic() - started_at > self.config.download_timeout and not terminated:
                process.terminate()
                terminated = True
            try:
                yield output.get(timeout=0.1)
            except queue.Empty:
                continue

        for thread in readers:
            thread.join(timeout=1)
        while not output.empty():
            yield output.get_nowait()

    def _save_download_success(
        self,
        video_info: Dict[str, Any],
        source_name: str,
        video_title: str,
        is_audio: bool = False,
    ) -> None:
        """Save last download metadata."""
        download_type = "MP3 Audio (320kbps)" if is_audio else f"{self.config.max_resolution}p MP4"
        self.state.save_last_download({
            "source": source_name,
            "title": video_title,
            "video_id": video_info["id"],
            "url": video_info["url"],
            "duration": video_info.get("duration_formatted", "Unknown"),
            "type": download_type,
            "private": True,
            "timestamp": datetime.now().isoformat(),
        })

    def download_playlist(
        self,
        playlist_url: str,
        download_type: str = "video",
        playlist_items: Optional[List[int]] = None,
    ) -> Tuple[bool, Optional[Path]]:
        """Download all or selected playlist entries using dual Rich progress."""
        try:
            playlist_info = self.scanner.get_playlist_info(playlist_url)
            if not playlist_info:
                console.print("[bold red]❌ Could not get playlist information[/bold red]")
                return False, None

            playlist_name = playlist_info["title"]
            uploader = playlist_info["uploader"]
            selected_count = len(set(playlist_items)) if playlist_items is not None else 0
            total_videos = selected_count or playlist_info["video_count"] or 1

            # Summary Panel
            info_table = Table.grid(padding=(0, 2))
            info_table.add_column(style="bold cyan", justify="right")
            info_table.add_column(style="white")
            info_table.add_row("📚 Playlist:", playlist_name)
            info_table.add_row("👤 Uploader:", uploader)
            info_table.add_row("🎬 Videos to Download:", str(total_videos))
            info_table.add_row("🎯 Type:", f"{'Audio (MP3)' if download_type == 'audio' else 'Video (MP4)'}")
            console.print(Panel(info_table, title="[bold blue]Starting Playlist Download[/bold blue]", border_style="blue"))

            archives_dir = self.config.log_dir / "archives"
            archives_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[<>:"/\\|?*]', '', playlist_name)
            download_archive = archives_dir / f"{safe_name}_archive.txt"

            cmd, playlist_dir = build_playlist_download_command(
                self.config,
                playlist_url,
                playlist_name,
                download_type=download_type,
                resume=True,
                playlist_items=playlist_items,
            )
            cmd.extend(["--download-archive", str(download_archive)])

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            current_video_idx = 1
            progress = create_playlist_progress()
            with progress:
                overall_task = progress.add_task(
                    f"[bold blue]Overall ({total_videos} videos)[/]",
                    total=100,
                    speed="",
                    eta="",
                )
                current_task = progress.add_task(
                    "[bold green]Current video[/]",
                    total=100,
                    speed="",
                    eta="",
                )

                for _, line in self._read_process_output(process):
                    p = self.parse_progress(line)
                    if p:
                        if p.get("type") == "playlist_progress":
                            try:
                                current_video_idx = int(p["current"])
                                total_videos = int(p["total"])
                            except ValueError:
                                pass
                            progress.update(
                                current_task,
                                completed=0,
                                description=f"[bold green]Item {current_video_idx}/{total_videos}[/]",
                            )
                        elif p.get("type") == "download" and "percent" in p:
                            try:
                                cur_pct = float(p["percent"])
                            except ValueError:
                                cur_pct = 0.0

                            overall_pct = ((current_video_idx - 1) / total_videos * 100) + (cur_pct / total_videos)
                            speed = p.get("speed", "")
                            eta = p.get("eta", "")

                            progress.update(
                                current_task,
                                completed=cur_pct,
                                speed=speed,
                                eta=eta,
                            )
                            progress.update(
                                overall_task,
                                completed=overall_pct,
                                description=f"[bold blue]Overall: Video {current_video_idx}/{total_videos}[/]",
                            )

            return_code = process.wait()
            has_files = any(playlist_dir.iterdir()) if playlist_dir.exists() else False

            if return_code == 0 or (return_code == 1 and has_files):
                console.print(f"[bold green]✅ Playlist download complete: {playlist_name}[/bold green]")
                return True, playlist_dir
            else:
                console.print(f"[bold red]❌ Playlist download completed with errors/skips[/bold red]")
                return False, playlist_dir

        except Exception as e:
            self.logger.error(f"❌ Error downloading playlist: {e}")
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
            return False, None

    def download_videos_parallel(self, download_tasks: List[Tuple[Dict[str, Any], str, str]]) -> int:
        """Download multiple videos concurrently using Rich multi-bar progress and thread pooling."""
        successful_downloads = 0
        if not download_tasks:
            return 0

        progress = create_parallel_progress()
        with progress:
            with ThreadPoolExecutor(max_workers=self.config.max_parallel_downloads) as executor:
                future_to_task = {}

                for video_info, source_name, task_type in download_tasks:
                    video_title = video_info.get("title", "Unknown")
                    display_title = (video_title[:30] + "…") if len(video_title) > 30 else video_title

                    task_id = progress.add_task(
                        f"[white]{display_title}[/white]",
                        source=source_name,
                        total=100,
                        visible=True,
                        speed="",
                        eta="",
                    )

                    future = executor.submit(
                        self.download_video,
                        video_info,
                        source_name,
                        is_manual=False,
                        progress=progress,
                        task_id=task_id,
                    )
                    future_to_task[future] = (video_info, source_name, task_type)

                for future in as_completed(future_to_task):
                    video_info, source_name, task_type = future_to_task[future]
                    try:
                        success, video_id = future.result()
                        if success:
                            successful_downloads += 1

                            if task_type == "channel":
                                handle = [k for k, v in self.state.channels.items() if v == source_name]
                                if handle:
                                    self.state.update_channel_history(handle[0], video_info)
                                    self.state.download_history["channels"][handle[0]] = video_id
                            elif task_type == "playlist":
                                playlist_url = [url for url, name in self.state.playlists.items() if name == source_name]
                                if playlist_url:
                                    self.state.update_channel_history(playlist_url[0], video_info)
                                    self.state.download_history["playlists"][playlist_url[0]] = video_id

                            self.state.save_download_history()
                    except Exception as e:
                        console.print(f"[bold red]❌ Error in parallel download for {source_name}: {e}[/bold red]")

        return successful_downloads
