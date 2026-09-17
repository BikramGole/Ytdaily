"""
YouTube channel and playlist scanner with video gap detection.
"""

import json
import logging
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple
from rich.tree import Tree
from ytdaily.config import Config
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.utils.cache import format_duration


class Scanner:
    """Scans YouTube channels and playlists for new content."""

    def __init__(self, config: Config, state: StateManager, logger: Optional[logging.Logger] = None):
        self.config = config
        self.state = state
        self.logger = logger or logging.getLogger("ytdaily")

    def get_all_recent_videos(
        self,
        url: str,
        source_name: str,
        max_videos: int = 100,
        silent: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get recent videos from a channel or playlist URL."""
        videos = []
        for attempt in range(self.config.max_retries):
            try:
                cmd = [
                    "yt-dlp",
                    "--flat-playlist",
                    "--playlist-items", f"1-{max_videos}",
                    "--dump-json",
                    "--no-warnings",
                    *self.config.get_cookie_args(),
                    url,
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.query_timeout * 2,
                    check=True,
                )

                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            video_id = data.get("id", "unknown")
                            title = data.get("title", "Unknown")
                            uploader = data.get("uploader", source_name)

                            duration = data.get("duration", 0)
                            if not duration:
                                duration = data.get("average_duration", 0)
                            if not duration:
                                duration = 0

                            videos.append({
                                "id": video_id,
                                "title": title,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "uploader": uploader,
                                "duration": duration,
                                "duration_formatted": format_duration(duration),
                            })
                        except json.JSONDecodeError:
                            continue

                    return videos

                return []

            except subprocess.TimeoutExpired:
                self.logger.warning(f"⚠️ Query timeout for {source_name} (attempt {attempt + 1})")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                continue

            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.strip() if e.stderr else "Unknown error"
                self.logger.error(f"❌ Query command failed for {source_name}: {error_msg}")
                if attempt == self.config.max_retries - 1:
                    return self._fallback_recent_videos(url, source_name, max_videos, silent)
                time.sleep(self.config.retry_delay)
                continue

            except Exception as e:
                self.logger.error(f"❌ Query error for {source_name}: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                continue

        return []

    def _fallback_recent_videos(
        self,
        url: str,
        source_name: str,
        limit: int,
        silent: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fallback query when flat playlist fails."""
        try:
            self.logger.info(f"🔄 Trying fallback query for {source_name}")
            videos = []
            max_videos = limit if self.state.is_first_run() else min(limit, 50)
            for i in range(1, max_videos + 1):
                try:
                    cmd = [
                        "yt-dlp",
                        "--flat-playlist",
                        "--playlist-items", str(i),
                        "--print", "%(id)s\t%(title)s\t%(uploader)s\t%(duration)s",
                        "--no-warnings",
                        *self.config.get_cookie_args(),
                        url,
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        parts = result.stdout.strip().split("\t")
                        if len(parts) >= 2:
                            video_id = parts[0]
                            title = parts[1] if len(parts) > 1 else "Unknown"
                            uploader = parts[2] if len(parts) > 2 else source_name
                            duration_str = parts[3] if len(parts) > 3 else "0"
                            try:
                                duration = int(duration_str) if duration_str.isdigit() else 0
                            except (ValueError, TypeError):
                                duration = 0

                            videos.append({
                                "id": video_id,
                                "title": title,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "uploader": uploader,
                                "duration": duration,
                                "duration_formatted": format_duration(duration),
                            })
                except Exception as e:
                    self.logger.warning(f"⚠️ Fallback video {i} failed for {source_name}: {e}")
                    break

            return videos
        except Exception as e:
            self.logger.error(f"❌ Fallback query failed for {source_name}: {e}")
            return []

    def get_video_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a single video (used for live preview before download)."""
        try:
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                "--no-warnings",
                *self.config.get_cookie_args(),
                video_url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip().split("\n")[0])
                duration = data.get("duration", 0) or 0
                return {
                    "id": data.get("id", ""),
                    "title": data.get("title", "Unknown Title"),
                    "uploader": data.get("uploader", "Unknown Uploader"),
                    "duration": duration,
                    "duration_formatted": format_duration(duration),
                    "thumbnail": data.get("thumbnail", ""),
                    "view_count": data.get("view_count", 0),
                    "upload_date": data.get("upload_date", ""),
                    "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                }
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch video info for {video_url}: {e}")
        return None

    def get_playlist_info(self, playlist_url: str) -> Optional[Dict[str, Any]]:
        """Get playlist title, uploader, and video count."""
        try:
            cmd = [
                "yt-dlp",
                "--flat-playlist",
                "--print", "%(playlist_title)s",
                "--print", "%(playlist_count)s",
                "--print", "%(uploader)s",
                "--no-download",
                "--no-warnings",
                *self.config.get_cookie_args(),
                playlist_url,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.query_timeout,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                playlist_title = lines[0] if len(lines) > 0 else "Unknown Playlist"
                video_count = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 0
                uploader = lines[2] if len(lines) > 2 else "Unknown"
                return {
                    "title": playlist_title,
                    "uploader": uploader,
                    "video_count": video_count,
                }
            else:
                # Fallback for just title
                cmd = [
                    "yt-dlp",
                    "--print", "%(title)s",
                    "--no-download",
                    "--no-warnings",
                    *self.config.get_cookie_args(),
                    playlist_url,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.query_timeout, check=False)
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        "title": result.stdout.strip(),
                        "uploader": "Unknown",
                        "video_count": 0,
                    }
        except Exception as e:
            self.logger.error(f"❌ Error getting playlist info: {e}")
        return None

    def check_subtitles_available(self, video_url: str) -> bool:
        """Check if subtitles are available to avoid 429 errors."""
        try:
            cmd = [
                "yt-dlp",
                "--list-subs",
                "--no-warnings",
                *self.config.get_cookie_args(),
                video_url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "Language" in line and "Formats" in line:
                        if len(lines) > 2:
                            return True
                    if line.startswith("en ") or "english" in line.lower():
                        return True
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ Could not check subtitles: {e}")
            return False

    def process_channel_auto(self, handle: str, display_name: str) -> List[Tuple[Dict[str, Any], str, str]]:
        """Queue only the newest video from a channel when not yet downloaded."""
        download_tasks = []
        with console.status(f"[bold blue]🔍 Checking {display_name}...[/]"):
            recent_videos = self.get_all_recent_videos(
                f"https://www.youtube.com/@{handle}/videos",
                display_name,
                max_videos=1,
                silent=True,
            )

        if not recent_videos:
            console.print(f"[dim]🔍 {display_name}: No new videos[/dim]")
            return []

        recent_videos = recent_videos[:1]
        shorts_skipped = 0
        new_videos = []

        for video_info in recent_videos:
            video_id = video_info["id"]
            if self.config.filter_shorts and video_info.get("duration", 0) < 60:
                shorts_skipped += 1
                continue
            if self.state.is_video_downloaded(handle, video_id):
                continue
            download_tasks.append((video_info, display_name, "channel"))
            new_videos.append(video_info)

        if new_videos:
            tree = Tree(f"[bold blue]🔍 {display_name}[/]")
            tree.add(f"[bold green]✅ Found {len(new_videos)} NEW video[/]")
            if shorts_skipped > 0:
                tree.add(f"[dim]⏭️ Skipped {shorts_skipped} Shorts (<60s)[/dim]")
            node = tree.add(f"📥 [bold]1[/bold] to download")
            node.add(f"[cyan]{new_videos[0].get('title', 'Unknown')}[/cyan]")
            console.print(tree)
            console.print("")
        else:
            msg = f"[dim]🔍 {display_name}: No new videos[/dim]"
            if shorts_skipped > 0:
                msg += f" [dim](skipped {shorts_skipped} Shorts)[/dim]"
            console.print(msg)

        return download_tasks

    def process_playlist_auto(self, playlist_url: str, playlist_name: str) -> List[Tuple[Dict[str, Any], str, str]]:
        """Queue only the newest video from a playlist when not yet downloaded."""
        download_tasks = []
        with console.status(f"[bold blue]🔍 Checking {playlist_name}...[/]"):
            recent_videos = self.get_all_recent_videos(playlist_url, playlist_name, max_videos=1, silent=True)

        if not recent_videos:
            console.print(f"[dim]🔍 {playlist_name}: No videos found or error[/dim]")
            return []

        recent_videos = recent_videos[:1]
        shorts_skipped = 0
        new_videos = []

        for video_info in recent_videos:
            video_id = video_info["id"]
            if self.config.filter_shorts and video_info.get("duration", 0) < 60:
                shorts_skipped += 1
                continue
            if self.state.is_video_downloaded(playlist_url, video_id):
                continue
            download_tasks.append((video_info, playlist_name, "playlist"))
            new_videos.append(video_info)

        if new_videos:
            tree = Tree(f"[bold blue]🔍 {playlist_name}[/]")
            tree.add(f"[bold green]✅ Found {len(new_videos)} NEW video[/]")
            if shorts_skipped > 0:
                tree.add(f"[dim]⏭️ Skipped {shorts_skipped} Shorts (<60s)[/dim]")
            node = tree.add(f"📥 [bold]1[/bold] to download")
            node.add(f"[cyan]{new_videos[0].get('title', 'Unknown')}[/cyan]")
            console.print(tree)
            console.print("")
        else:
            msg = f"[dim]🔍 {playlist_name}: No new videos[/dim]"
            if shorts_skipped > 0:
                msg += f" [dim](skipped {shorts_skipped} Shorts)[/dim]"
            console.print(msg)

        return download_tasks

    def process_channel_first_run(
        self,
        handle_or_url: str,
        display_name: str,
        video_limit: int,
        item_type: str = "channel",
    ) -> List[Tuple[Dict[str, Any], str, str]]:
        """Process a channel or playlist on first run with limit."""
        if video_limit == 0:
            console.print(f"[dim]🔍 {display_name}: Skipped (limit 0)[/dim]")
            return []

        target_url = (
            f"https://www.youtube.com/@{handle_or_url}/videos"
            if item_type == "channel"
            else handle_or_url
        )

        with console.status(f"[bold blue]🔍 Scanning {display_name}...[/]"):
            recent_videos = self.get_all_recent_videos(
                target_url,
                display_name,
                max_videos=max(video_limit, 20),
                silent=True,
            )

        if not recent_videos:
            console.print(f"[dim]🔍 {display_name}: No videos found or error[/dim]")
            return []

        if len(recent_videos) > video_limit:
            videos_to_process = recent_videos[:video_limit]
            videos_to_mark = recent_videos[video_limit:]
            for v in videos_to_mark:
                self.state.update_channel_history(handle_or_url, v)
            recent_videos = videos_to_process

        download_tasks = []
        for video_info in recent_videos:
            download_tasks.append((video_info, display_name, item_type))

        tree = Tree(f"[bold blue]🔍 {display_name}[/]")
        tree.add(f"[bold green]✅ Found {len(recent_videos)} videos to download[/]")
        node = tree.add(f"📥 [bold]{len(recent_videos)}[/bold] videos")
        for i, video_info in enumerate(recent_videos):
            if i < 3:
                node.add(f"[cyan]{video_info.get('title', 'Unknown')}[/cyan]")
        if len(recent_videos) > 3:
            node.add(f"[dim]... and {len(recent_videos) - 3} more[/dim]")

        console.print(tree)
        console.print("")
        return download_tasks
