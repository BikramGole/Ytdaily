"""
Thread-safe JSON state management for Ytdaily.
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from ytdaily.config import Config


class StateManager:
    """Manages persistent JSON state files with thread locks."""

    def __init__(self, config: Config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("ytdaily")
        self._lock = threading.Lock()

        self.channels: Dict[str, str] = {}
        self.playlists: Dict[str, str] = {}
        self.download_history: Dict[str, Any] = {"channels": {}, "playlists": {}}
        self.last_download: Dict[str, Any] = {}
        self.resume_state: Dict[str, Any] = {"videos": {}, "playlists": {}, "last_cleanup": datetime.now().isoformat()}
        self.channel_history: Dict[str, Any] = {"channels": {}, "last_updated": datetime.now().isoformat(), "first_run_completed": False}

        self.load_all()

    def load_all(self) -> None:
        """Load all state files from disk."""
        self.load_config()
        self.load_download_history()
        self.load_resume_state()
        self.load_channel_history()

    # --- CONFIG ---
    def load_config(self) -> None:
        """Load configuration and monitored sources from file."""
        with self._lock:
            try:
                if self.config.config_path.exists():
                    with open(self.config.config_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)

                    if not isinstance(config_data, dict):
                        config_data = {}

                    self.channels = config_data.get("channels", {})
                    self.playlists = config_data.get("playlists", {})

                    # Settings
                    self.config.ask_initial_videos = bool(config_data.get("ask_initial_videos", True))
                    self.config.initial_videos_per_channel = int(config_data.get("initial_videos_per_channel", 5))
                    self.config.max_videos_per_channel = int(config_data.get("max_videos_per_channel", 100))
                    self.config.max_resolution = str(config_data.get("max_resolution", "720"))
                    self.config.browser = str(config_data.get("browser", "auto"))

                    if "cleanup_days" in config_data:
                        self.config.cleanup_days = int(config_data["cleanup_days"])
                    if "filter_shorts" in config_data:
                        self.config.filter_shorts = bool(config_data["filter_shorts"])
                    if "max_parallel_downloads" in config_data:
                        self.config.max_parallel_downloads = int(config_data["max_parallel_downloads"])
                    if "resume_cache_days" in config_data:
                        self.config.resume_cache_days = int(config_data["resume_cache_days"])

                    # Optional configurable directory paths
                    if "base_video_dir" in config_data and config_data["base_video_dir"]:
                        self.config.base_video_dir = Path(config_data["base_video_dir"])
                    if "base_audio_dir" in config_data and config_data["base_audio_dir"]:
                        self.config.base_audio_dir = Path(config_data["base_audio_dir"])

                    self.config.validate()
                else:
                    self.channels = {}
                    self.playlists = {}
                    self._save_config_locked()
            except Exception as e:
                self.logger.error(f"❌ Error loading config: {e}")
                self.channels = {}
                self.playlists = {}

    def save_config(self) -> None:
        """Save configuration and sources to file."""
        with self._lock:
            self._save_config_locked()

    def _save_config_locked(self) -> None:
        try:
            config_data = {
                "channels": self.channels,
                "playlists": self.playlists,
                "ask_initial_videos": self.config.ask_initial_videos,
                "initial_videos_per_channel": self.config.initial_videos_per_channel,
                "max_videos_per_channel": self.config.max_videos_per_channel,
                "max_resolution": self.config.max_resolution,
                "browser": self.config.browser,
                "cleanup_days": self.config.cleanup_days,
                "filter_shorts": self.config.filter_shorts,
                "max_parallel_downloads": self.config.max_parallel_downloads,
                "resume_cache_days": self.config.resume_cache_days,
                "base_video_dir": str(self.config.base_video_dir),
                "base_audio_dir": str(self.config.base_audio_dir),
            }
            with open(self.config.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.logger.debug("💾 Saved configuration")
        except IOError as e:
            self.logger.error(f"❌ Error saving config: {e}")

    # --- CHANNEL HISTORY ---
    def load_channel_history(self) -> None:
        """Load channel history tracking all downloaded videos."""
        with self._lock:
            try:
                if self.config.channel_history_path.exists():
                    with open(self.config.channel_history_path, "r", encoding="utf-8") as f:
                        self.channel_history = json.load(f)
                else:
                    self.channel_history = {
                        "channels": {},
                        "last_updated": datetime.now().isoformat(),
                        "first_run_completed": False,
                    }
                    self._save_channel_history_locked()
            except Exception as e:
                self.logger.error(f"❌ Error loading channel history: {e}")
                self.channel_history = {
                    "channels": {},
                    "last_updated": datetime.now().isoformat(),
                    "first_run_completed": False,
                }
                self._save_channel_history_locked()

    def save_channel_history(self) -> None:
        """Save channel history to disk."""
        with self._lock:
            self._save_channel_history_locked()

    def _save_channel_history_locked(self) -> None:
        try:
            self.channel_history["last_updated"] = datetime.now().isoformat()
            with open(self.config.channel_history_path, "w", encoding="utf-8") as f:
                json.dump(self.channel_history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"❌ Error saving channel history: {e}")

    def mark_first_run_completed(self) -> None:
        """Mark first run completed."""
        with self._lock:
            self.channel_history["first_run_completed"] = True
            self._save_channel_history_locked()

    def is_first_run(self) -> bool:
        """Check if first run has not completed."""
        with self._lock:
            return not self.channel_history.get("first_run_completed", False)

    def update_channel_history(self, channel_handle_or_url: str, video_info: Dict[str, Any]) -> None:
        """Add a video to channel history."""
        with self._lock:
            try:
                if "channels" not in self.channel_history:
                    self.channel_history["channels"] = {}

                if channel_handle_or_url not in self.channel_history["channels"]:
                    self.channel_history["channels"][channel_handle_or_url] = {
                        "downloaded_videos": [],
                        "last_download": datetime.now().isoformat(),
                    }

                video_id = video_info.get("id")
                if not video_id:
                    return

                existing_ids = [
                    v["id"] for v in self.channel_history["channels"][channel_handle_or_url]["downloaded_videos"]
                ]
                if video_id not in existing_ids:
                    self.channel_history["channels"][channel_handle_or_url]["downloaded_videos"].append({
                        "id": video_id,
                        "title": video_info.get("title", "Unknown"),
                        "url": video_info.get("url", f"https://www.youtube.com/watch?v={video_id}"),
                        "downloaded_at": datetime.now().isoformat(),
                    })
                    # Keep maximum 1000 items per source
                    if len(self.channel_history["channels"][channel_handle_or_url]["downloaded_videos"]) > 1000:
                        self.channel_history["channels"][channel_handle_or_url]["downloaded_videos"] = (
                            self.channel_history["channels"][channel_handle_or_url]["downloaded_videos"][-1000:]
                        )

                    self.channel_history["channels"][channel_handle_or_url]["last_download"] = datetime.now().isoformat()
                    self._save_channel_history_locked()
            except Exception as e:
                self.logger.warning(f"⚠️ Could not update channel history: {e}")

    def is_video_downloaded(self, channel_handle_or_url: str, video_id: str) -> bool:
        """Check if a video has already been recorded in channel history."""
        with self._lock:
            try:
                channel_data = self.channel_history.get("channels", {}).get(channel_handle_or_url, {})
                videos = channel_data.get("downloaded_videos", [])
                return any(v.get("id") == video_id for v in videos)
            except Exception:
                return False

    # --- RESUME STATE ---
    def load_resume_state(self) -> None:
        """Load resume state from disk."""
        with self._lock:
            try:
                if self.config.resume_state_path.exists():
                    with open(self.config.resume_state_path, "r", encoding="utf-8") as f:
                        self.resume_state = json.load(f)
                else:
                    self.resume_state = {"videos": {}, "playlists": {}, "last_cleanup": datetime.now().isoformat()}
                    self._save_resume_state_locked()
            except Exception as e:
                self.logger.error(f"❌ Error loading resume state: {e}")
                self.resume_state = {"videos": {}, "playlists": {}, "last_cleanup": datetime.now().isoformat()}
                self._save_resume_state_locked()

    def save_resume_state(self) -> None:
        with self._lock:
            self._save_resume_state_locked()

    def _save_resume_state_locked(self) -> None:
        try:
            with open(self.config.resume_state_path, "w", encoding="utf-8") as f:
                json.dump(self.resume_state, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"❌ Error saving resume state: {e}")

    def cleanup_old_resume_entries(self) -> int:
        """Clean up resume entries older than configured days."""
        cleaned_count = 0
        with self._lock:
            try:
                cutoff_time = datetime.now() - timedelta(days=self.config.resume_cache_days)
                for key in ["videos", "playlists"]:
                    for item_id in list(self.resume_state.get(key, {}).keys()):
                        entry = self.resume_state[key][item_id]
                        entry_time_str = entry.get("timestamp", "2000-01-01T00:00:00")
                        try:
                            entry_time = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                            if entry_time.tzinfo:
                                entry_time = entry_time.replace(tzinfo=None)
                            if entry_time < cutoff_time:
                                del self.resume_state[key][item_id]
                                cleaned_count += 1
                        except Exception:
                            del self.resume_state[key][item_id]
                            cleaned_count += 1

                if cleaned_count > 0:
                    self._save_resume_state_locked()
            except Exception as e:
                self.logger.error(f"❌ Error cleaning up old resume entries: {e}")
        return cleaned_count

    def update_resume_state(self, item_type: str, item_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            section = "videos" if item_type in ("video", "audio") else "playlists"
            if section not in self.resume_state:
                self.resume_state[section] = {}
            self.resume_state[section][item_id] = {**data, "timestamp": datetime.now().isoformat()}
            self._save_resume_state_locked()

    def get_resume_state(self, item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            section = "videos" if item_type in ("video", "audio") else "playlists"
            return self.resume_state.get(section, {}).get(item_id)

    def clear_resume_state(self, item_type: str, item_id: str) -> None:
        with self._lock:
            section = "videos" if item_type in ("video", "audio") else "playlists"
            if section in self.resume_state and item_id in self.resume_state[section]:
                del self.resume_state[section][item_id]
                self._save_resume_state_locked()

    def clear_all_resume_data(self) -> None:
        with self._lock:
            self.resume_state = {
                "videos": {},
                "playlists": {},
                "last_cleanup": datetime.now().isoformat(),
            }
            self._save_resume_state_locked()

    # --- DOWNLOAD HISTORY ---
    def load_download_history(self) -> None:
        with self._lock:
            try:
                if self.config.download_log_path.exists():
                    with open(self.config.download_log_path, "r", encoding="utf-8") as f:
                        self.download_history = json.load(f)
                else:
                    self.download_history = {"channels": {}, "playlists": {}}
                    self._save_download_history_locked()

                if self.config.last_download_path.exists():
                    with open(self.config.last_download_path, "r", encoding="utf-8") as f:
                        self.last_download = json.load(f)
                else:
                    self.last_download = {}
            except Exception as e:
                self.logger.error(f"❌ Error loading download history: {e}")
                self.download_history = {"channels": {}, "playlists": {}}
                self.last_download = {}

    def save_download_history(self) -> None:
        with self._lock:
            self._save_download_history_locked()

    def _save_download_history_locked(self) -> None:
        try:
            with open(self.config.download_log_path, "w", encoding="utf-8") as f:
                json.dump(self.download_history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"❌ Error saving download history: {e}")

    def save_last_download(self, info: Dict[str, Any]) -> None:
        with self._lock:
            try:
                self.last_download = {**info, "timestamp": datetime.now().isoformat()}
                with open(self.config.last_download_path, "w", encoding="utf-8") as f:
                    json.dump(self.last_download, f, indent=2, ensure_ascii=False)
            except IOError as e:
                self.logger.warning(f"⚠️ Could not save last download info: {e}")

    def get_last_download(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.last_download)

    # --- QUERY HELPERS FOR HISTORY VIEWER ---
    def get_all_downloaded_videos(self, query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve flattened list of downloaded videos, optionally filtered."""
        results = []
        with self._lock:
            for source_id, data in self.channel_history.get("channels", {}).items():
                source_name = self.channels.get(source_id) or self.playlists.get(source_id) or source_id
                for v in data.get("downloaded_videos", []):
                    item = {
                        "source": source_name,
                        "source_id": source_id,
                        "title": v.get("title", "Unknown"),
                        "video_id": v.get("id", ""),
                        "url": v.get("url", ""),
                        "downloaded_at": v.get("downloaded_at", ""),
                    }
                    if query:
                        q = query.lower()
                        if (
                            q in item["title"].lower()
                            or q in item["source"].lower()
                            or q in item["video_id"].lower()
                        ):
                            results.append(item)
                    else:
                        results.append(item)

        # Sort newest first
        results.sort(key=lambda x: x.get("downloaded_at", ""), reverse=True)
        return results[:limit]
