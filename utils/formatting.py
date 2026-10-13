import math

def format_bytes(size_bytes: float) -> str:
    """Format bytes to human readable string (KB, MB, GB)."""
    if size_bytes is None or size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {units[i]}"

def format_speed(speed_bytes_per_sec: float) -> str:
    """Format speed in bytes/sec to human readable format."""
    if speed_bytes_per_sec is None or speed_bytes_per_sec <= 0:
        return "0 B/s"
    return f"{format_bytes(speed_bytes_per_sec)}/s"

def format_duration(seconds: float) -> str:
    """Format duration into HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    sec = int(seconds)
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    rem_sec = sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{rem_sec:02d}"
    return f"{minutes:02d}:{rem_sec:02d}"

def format_eta(seconds: float) -> str:
    """Format ETA seconds."""
    if seconds is None or seconds <= 0:
        return "--:--"
    return format_duration(seconds)
