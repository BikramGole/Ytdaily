import sys
import subprocess
import shutil
from pathlib import Path
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

def open_file(file_path: Path):
    """Open a file with the system default application."""
    if not file_path.exists():
        return False
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))

def open_folder(folder_path: Path):
    """Open the containing directory in system file explorer."""
    target = folder_path if folder_path.is_dir() else folder_path.parent
    if not target.exists():
        return False
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

def check_ffmpeg() -> bool:
    """Check if ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None

def check_ytdlp() -> bool:
    """Check if yt-dlp Python package is available."""
    try:
        import yt_dlp
        return True
    except ImportError:
        return False
