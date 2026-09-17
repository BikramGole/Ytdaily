"""
Logging setup and rotation for Ytdaily.
"""

import logging
import logging.handlers
from pathlib import Path


def setup_log_cleanup(log_dir: Path, max_log_files: int = 10) -> None:
    """Setup log rotation and cleanup."""
    if not log_dir.exists():
        return
    log_files = list(log_dir.glob("YT_feed*.log*"))
    if len(log_files) > max_log_files:
        log_files.sort(key=lambda x: x.stat().st_mtime)
        for old_log in log_files[:-max_log_files]:
            try:
                old_log.unlink()
            except OSError:
                pass


def setup_logging(
    app_log_path: Path,
    max_log_size: int = 5 * 1024 * 1024,
    max_log_files: int = 10,
) -> logging.Logger:
    """Configure file logging with rotation."""
    app_log_path.parent.mkdir(parents=True, exist_ok=True)
    setup_log_cleanup(app_log_path.parent, max_log_files)

    file_handler = logging.handlers.RotatingFileHandler(
        app_log_path,
        maxBytes=max_log_size,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    logger = logging.getLogger("ytdaily")
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    logger.addHandler(file_handler)

    return logger
