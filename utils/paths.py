import os
import sys
from pathlib import Path

def get_app_data_dir() -> Path:
    """Return platform-aware application data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else: # Linux / Unix
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    app_dir = base / "YTDaily"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def get_config_dir() -> Path:
    """Return platform-aware config directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    
    cfg_dir = base / "YTDaily"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir

def get_default_download_dir() -> Path:
    """Return platform-aware default video download directory."""
    if sys.platform == "win32":
        vids = Path.home() / "Videos"
    elif sys.platform == "darwin":
        vids = Path.home() / "Movies"
    else:
        # Check XDG user dirs if available
        xdg_videos = os.environ.get("XDG_VIDEOS_DIR")
        if xdg_videos and Path(xdg_videos).exists():
            vids = Path(xdg_videos)
        else:
            vids = Path.home() / "Videos"
    
    yt_feed = vids / "YT_feed"
    yt_feed.mkdir(parents=True, exist_ok=True)
    return yt_feed

def get_default_audio_dir() -> Path:
    """Return platform-aware default audio/music directory."""
    if sys.platform == "win32":
        music = Path.home() / "Music"
    elif sys.platform == "darwin":
        music = Path.home() / "Music"
    else:
        xdg_music = os.environ.get("XDG_MUSIC_DIR")
        if xdg_music and Path(xdg_music).exists():
            music = Path(xdg_music)
        else:
            music = Path.home() / "Music"
    
    yt_music = music / "YT_music"
    yt_music.mkdir(parents=True, exist_ok=True)
    return yt_music
