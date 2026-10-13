"""
SQLite-backed persistent storage for YTDaily.
Handles download history, settings, subscriptions.
Migrates from legacy JSON files if found.
"""

import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from utils.paths import get_app_data_dir, get_config_dir, get_default_download_dir, get_default_audio_dir


DB_VERSION = 1


def _get_db_path() -> Path:
    return get_app_data_dir() / "ytdaily.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                channel TEXT NOT NULL DEFAULT '',
                downloaded_at TEXT NOT NULL,
                file_path TEXT NOT NULL DEFAULT '',
                output_format TEXT NOT NULL DEFAULT 'mp4',
                quality TEXT NOT NULL DEFAULT 'best',
                status TEXT NOT NULL DEFAULT 'completed',
                error_msg TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                channel_id TEXT NOT NULL DEFAULT '',
                last_checked TEXT,
                auto_download INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_url ON history(url);
            CREATE INDEX IF NOT EXISTS idx_history_video_id ON history(video_id);
            CREATE INDEX IF NOT EXISTS idx_history_status ON history(status);
        """)

        # Ensure version row
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version VALUES (?)", (DB_VERSION,))

    conn.close()
    _migrate_from_json()


def _migrate_from_json():
    """One-time migration from legacy YT_daily JSON files."""
    # Check for legacy channel_history.json
    legacy_dirs = [
        Path.home() / ".YT_log",
        get_config_dir(),
    ]
    for legacy_dir in legacy_dirs:
        ch_file = legacy_dir / "channel_history.json"
        if ch_file.exists():
            try:
                with open(ch_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                channels = data.get("channels", {})
                conn = get_connection()
                with conn:
                    for handle, ch_data in channels.items():
                        for vid in ch_data.get("downloaded_videos", []):
                            try:
                                conn.execute(
                                    """INSERT OR IGNORE INTO history
                                    (video_id, url, title, channel, downloaded_at, file_path, output_format, quality, status)
                                    VALUES (?,?,?,?,?,?,?,?,?)""",
                                    (
                                        vid.get("id", ""),
                                        vid.get("url", ""),
                                        vid.get("title", "Unknown"),
                                        handle,
                                        vid.get("downloaded_at", datetime.now().isoformat()),
                                        "",
                                        "mp4",
                                        "720",
                                        "completed",
                                    ),
                                )
                            except Exception:
                                pass
                conn.close()
                # Backup the legacy file so we don't re-import
                shutil.copy2(str(ch_file), str(ch_file.with_suffix(".json.bak")))
            except Exception as e:
                print(f"[migration] Warning: {e}")
            break  # only migrate once


# ─── History ──────────────────────────────────────────────────────────────────

def add_history(video_id: str, url: str, title: str, channel: str,
                file_path: str, output_format: str, quality: str,
                status: str = "completed", error_msg: str = "") -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """INSERT INTO history
               (video_id, url, title, channel, downloaded_at, file_path, output_format, quality, status, error_msg)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (video_id, url, title, channel, datetime.now().isoformat(),
             file_path, output_format, quality, status, error_msg),
        )
        return cur.lastrowid
    conn.close()


def update_history_status(row_id: int, status: str, file_path: str = "", error_msg: str = ""):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE history SET status=?, file_path=?, error_msg=? WHERE id=?",
            (status, file_path, error_msg, row_id),
        )
    conn.close()


def get_history(search: str = "", limit: int = 500) -> List[Dict]:
    conn = get_connection()
    if search:
        q = f"%{search}%"
        rows = conn.execute(
            """SELECT * FROM history WHERE title LIKE ? OR channel LIKE ? OR url LIKE ?
               ORDER BY downloaded_at DESC LIMIT ?""",
            (q, q, q, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY downloaded_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_history(row_id: int):
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM history WHERE id=?", (row_id,))
    conn.close()


def get_history_stats() -> Dict[str, int]:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM history WHERE status='completed'"
    ).fetchone()[0]
    failed = conn.execute(
        "SELECT COUNT(*) FROM history WHERE status='failed'"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "completed": completed, "failed": failed}


# ─── Subscriptions ────────────────────────────────────────────────────────────

def add_subscription(name: str, url: str, channel_id: str = "", auto_download: bool = False) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT OR REPLACE INTO subscriptions (name, url, channel_id, auto_download) VALUES (?,?,?,?)",
            (name, url, channel_id, int(auto_download)),
        )
        return cur.lastrowid
    conn.close()


def get_subscriptions() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM subscriptions ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_subscription(row_id: int):
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM subscriptions WHERE id=?", (row_id,))
    conn.close()


def update_subscription_checked(row_id: int):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE subscriptions SET last_checked=? WHERE id=?",
            (datetime.now().isoformat(), row_id),
        )
    conn.close()


# ─── Settings ─────────────────────────────────────────────────────────────────

_DEFAULT_SETTINGS: Dict[str, str] = {
    "theme": "catppuccin-mocha",
    "download_dir": str(get_default_download_dir()),
    "audio_dir": str(get_default_audio_dir()),
    "default_quality": "1080",
    "default_format": "mp4",
    "concurrent_downloads": "2",
    "auto_start_queue": "true",
    "overwrite_existing": "false",
    "audio_format": "m4a",
    "audio_quality": "best",
    "embed_subs": "false",
    "sub_lang": "en",
    "ffmpeg_path": "",
    "proxy": "",
    "cookies_file": "",
    "custom_ytdlp_args": "",
    "filter_shorts": "true",
    "cleanup_days": "60",
    "browser": "auto",
}


def get_setting(key: str) -> str:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    if row:
        return row["value"]
    return _DEFAULT_SETTINGS.get(key, "")


def set_setting(key: str, value: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value))
        )
    conn.close()


def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    result = dict(_DEFAULT_SETTINGS)
    result.update({r["key"]: r["value"] for r in rows})
    return result


def bulk_save_settings(settings: Dict[str, str]):
    conn = get_connection()
    with conn:
        for k, v in settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, str(v))
            )
    conn.close()
