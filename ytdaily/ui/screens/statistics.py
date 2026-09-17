"""
Statistics dashboard screen for Ytdaily.
"""

from datetime import datetime
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box
from ytdaily.config import Config
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_string
from ytdaily.utils.browser import detect_browser
from ytdaily.utils.system import get_disk_space_info


def show_statistics(config: Config, state: StateManager) -> None:
    """Render the full statistics and storage dashboard."""
    console.print("")
    console.print(Rule("[bold magenta]📊 System Statistics & Analytics Dashboard[/bold magenta]"))
    console.print("")

    # Configuration summary table
    config_table = Table(show_header=False, box=box.SIMPLE)
    config_table.add_column("Key", style="bold cyan", width=26)
    config_table.add_column("Value", style="white")

    config_table.add_row("📁 Video Directory", str(config.current_video_dir))
    config_table.add_row("🎧 Audio Directory", str(config.current_audio_dir))
    config_table.add_row("📚 Playlist Directory", str(config.current_playlist_dir))
    config_table.add_row("📻 Podcast Directory", str(config.current_podcast_dir))
    config_table.add_row("📺 Channels Monitored", str(len(state.channels)))
    config_table.add_row("📋 Playlists Monitored", str(len(state.playlists)))
    config_table.add_row("⚡ Parallel Downloads", str(config.max_parallel_downloads))

    browser_disp = config.browser
    if browser_disp == "auto":
        browser_disp = f"auto (detected: {detect_browser()})"
    config_table.add_row("🍪 Browser Cookies", browser_disp)
    config_table.add_row("🔄 Resume Cache Days", f"{config.resume_cache_days} days")
    config_table.add_row("✅ First Run Completed", "No (First run pending)" if state.is_first_run() else "Yes")
    config_table.add_row("🧹 Video Retention", f"{config.cleanup_days} days")
    config_table.add_row("⏱️ Shorts Filter", "Enabled (<60s skipped)" if config.filter_shorts else "Disabled")

    console.print(Panel(config_table, title="[bold blue]Active Configuration[/bold blue]", border_style="blue", box=box.ROUNDED))
    console.print("")

    # Metrics computation
    total_tracked = sum(
        len(ch.get("downloaded_videos", []))
        for ch in state.channel_history.get("channels", {}).values()
    )
    video_resume_count = len(state.resume_state.get("videos", {}))
    playlist_resume_count = len(state.resume_state.get("playlists", {}))

    video_files = list(config.current_video_dir.glob("*.mp4")) if config.current_video_dir.exists() else []
    audio_files = list(config.current_audio_dir.glob("*.mp3")) if config.current_audio_dir.exists() else []

    playlist_dirs = [d for d in config.current_playlist_dir.iterdir() if d.is_dir()] if config.current_playlist_dir.exists() else []
    podcast_dirs = [d for d in config.current_podcast_dir.iterdir() if d.is_dir()] if config.current_podcast_dir.exists() else []

    playlist_videos = sum(len(list(p.glob("*.mp4"))) for p in playlist_dirs)
    podcast_files = sum(len(list(p.glob("*.mp3"))) for p in podcast_dirs)

    # Metrics table
    metrics_table = Table(box=box.ROUNDED, header_style="bold magenta")
    metrics_table.add_column("Library / State Metric", style="cyan")
    metrics_table.add_column("Count / Value", style="bold green", justify="right")

    metrics_table.add_row("📥 Total Videos Ever Tracked", str(total_tracked))
    metrics_table.add_row("🎬 Videos In Feed Folder", f"{len(video_files)} files")
    metrics_table.add_row("🎧 Audio In Music Folder", f"{len(audio_files)} files")
    metrics_table.add_row("📚 Video Playlists On Disk", f"{len(playlist_dirs)} ({playlist_videos} videos)")
    metrics_table.add_row("📻 Podcast Playlists On Disk", f"{len(podcast_dirs)} ({podcast_files} tracks)")
    metrics_table.add_row("📋 Active Incomplete Resume States", f"{video_resume_count} videos, {playlist_resume_count} playlists")

    disk = get_disk_space_info(config.base_video_dir)
    metrics_table.add_row("💾 Storage Free Space", f"{disk.get('free_gb', 'N/A')} ({disk.get('used_percent', 'N/A')} used)")

    console.print(Panel(metrics_table, title="[bold green]Media Library & Download Statistics[/bold green]", border_style="green", box=box.ROUNDED))
    console.print("")

    # Last download card
    last_dl = state.get_last_download()
    if last_dl and "timestamp" in last_dl:
        try:
            dt = datetime.fromisoformat(last_dl["timestamp"].replace("Z", "+00:00"))
            formatted_time = dt.strftime("%b %d, %Y at %I:%M %p")
        except Exception:
            formatted_time = last_dl.get("timestamp", "Unknown")

        last_table = Table.grid(padding=(0, 2))
        last_table.add_column(style="bold cyan", justify="right")
        last_table.add_column(style="white")
        last_table.add_row("🕒 Completed At:", formatted_time)
        last_table.add_row("📖 Channel / Source:", last_dl.get("source", "Unknown"))
        last_table.add_row("🎬 Video Title:", last_dl.get("title", "Unknown"))
        last_table.add_row("⏱️ Duration & Format:", f"{last_dl.get('duration', 'Unknown')} ({last_dl.get('type', 'Video')})")
        if "url" in last_dl:
            last_table.add_row("🔗 Video URL:", last_dl.get("url", ""))

        console.print(Panel(last_table, title="[bold yellow]Last Download Activity[/bold yellow]", border_style="yellow", box=box.ROUNDED))
        console.print("")

    ask_string("Press Enter to return to main menu...", allow_empty=True)
