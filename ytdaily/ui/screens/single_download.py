"""
Single video, single audio, and interactive playlist download screens with live preview.
"""

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box
from ytdaily.config import Config
from ytdaily.core.downloader import Downloader
from ytdaily.core.scanner import Scanner
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_string, ask_choice, ask_confirm


def download_single_video_interactive(downloader: Downloader, scanner: Scanner) -> None:
    """Download a single video with live metadata preview."""
    console.print("")
    console.print(Rule("[bold cyan]🎬 Single Video Download[/bold cyan]"))
    console.print("")

    url = ask_string("Enter YouTube video URL (or press Enter to cancel):", allow_empty=True)
    if not url:
        return

    with console.status("[bold blue]🔍 Fetching video details for live preview...[/bold blue]"):
        video_info = scanner.get_video_info(url)

    if not video_info:
        console.print("[bold red]❌ Could not fetch video details. Please check the URL and your connection.[/bold red]")
        ask_string("Press Enter to return...", allow_empty=True)
        return

    # Live preview card
    preview_table = Table.grid(padding=(0, 2))
    preview_table.add_column(style="bold cyan", justify="right")
    preview_table.add_column(style="white")

    preview_table.add_row("🎬 Title:", video_info.get("title", "Unknown"))
    preview_table.add_row("👤 Channel:", video_info.get("uploader", "Unknown"))
    preview_table.add_row("⏱️ Duration:", video_info.get("duration_formatted", "Unknown"))
    if video_info.get("upload_date"):
        preview_table.add_row("📅 Uploaded:", video_info.get("upload_date"))
    if video_info.get("thumbnail"):
        preview_table.add_row("🖼️ Thumbnail:", f"[link={video_info['thumbnail']}]{video_info['thumbnail']}[/link]")

    console.print(
        Panel(
            preview_table,
            title="[bold green]Live Video Preview[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    if not ask_confirm("Start download now?", default=True):
        console.print("[dim]Download cancelled.[/dim]")
        return

    uploader = video_info.get("uploader", "Single Video")
    success, _ = downloader.download_video(video_info, uploader, is_manual=True, is_audio=False)

    if success:
        console.print("[bold green]✨ Video downloaded successfully![/bold green]")
    else:
        console.print("[bold red]❌ Video download failed.[/bold red]")

    ask_string("Press Enter to return...", allow_empty=True)


def download_single_audio_interactive(downloader: Downloader, scanner: Scanner) -> None:
    """Download a single audio track (320kbps MP3) with live preview."""
    console.print("")
    console.print(Rule("[bold magenta]🎧 Single Audio Download (320kbps MP3)[/bold magenta]"))
    console.print("")

    url = ask_string("Enter YouTube video URL (or press Enter to cancel):", allow_empty=True)
    if not url:
        return

    with console.status("[bold blue]🔍 Fetching track details for live preview...[/bold blue]"):
        video_info = scanner.get_video_info(url)

    if not video_info:
        console.print("[bold red]❌ Could not fetch audio details. Please check the URL.[/bold red]")
        ask_string("Press Enter to return...", allow_empty=True)
        return

    preview_table = Table.grid(padding=(0, 2))
    preview_table.add_column(style="bold cyan", justify="right")
    preview_table.add_column(style="white")

    preview_table.add_row("🎵 Track Title:", video_info.get("title", "Unknown"))
    preview_table.add_row("👤 Artist / Uploader:", video_info.get("uploader", "Unknown"))
    preview_table.add_row("⏱️ Duration:", video_info.get("duration_formatted", "Unknown"))
    if video_info.get("thumbnail"):
        preview_table.add_row("🖼️ Cover Art:", f"[link={video_info['thumbnail']}]{video_info['thumbnail']}[/link]")

    console.print(
        Panel(
            preview_table,
            title="[bold green]Live Audio Preview[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    if not ask_confirm("Start audio extraction now?", default=True):
        console.print("[dim]Download cancelled.[/dim]")
        return

    uploader = video_info.get("uploader", "Single Audio")
    success, _ = downloader.download_video(video_info, uploader, is_manual=True, is_audio=True)

    if success:
        console.print("[bold green]✨ Audio track downloaded successfully![/bold green]")
    else:
        console.print("[bold red]❌ Audio download failed.[/bold red]")

    ask_string("Press Enter to return...", allow_empty=True)


def download_playlist_interactive(
    downloader: Downloader,
    scanner: Scanner,
    config: Config,
) -> None:
    """Interactive playlist download screen with video or audio option."""
    console.print("")
    console.print(Rule("[bold blue]📚 Interactive Playlist Download[/bold blue]"))
    console.print("")

    url = ask_string("Enter YouTube playlist URL (or press Enter to cancel):", allow_empty=True)
    if not url:
        return

    with console.status("[bold blue]🔍 Fetching playlist metadata...[/bold blue]"):
        playlist_info = scanner.get_playlist_info(url)

    if not playlist_info:
        console.print("[bold red]❌ Could not inspect playlist. Please verify the URL.[/bold red]")
        ask_string("Press Enter to return...", allow_empty=True)
        return

    preview_table = Table.grid(padding=(0, 2))
    preview_table.add_column(style="bold cyan", justify="right")
    preview_table.add_column(style="white")
    preview_table.add_row("📚 Playlist Title:", playlist_info.get("title", "Unknown"))
    preview_table.add_row("👤 Creator:", playlist_info.get("uploader", "Unknown"))
    preview_table.add_row("🎬 Video Count:", str(playlist_info.get("video_count", "Unknown")))

    console.print(
        Panel(
            preview_table,
            title="[bold blue]Playlist Information[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    console.print("")
    console.print("🎯 [bold]Select Download Format:[/bold]")
    console.print(f"   1. 🎬 Video Playlist ({config.max_resolution}p MP4)")
    console.print("   2. 🎧 Podcast / Audio Playlist (320kbps MP3)")

    format_choice = ask_choice("Select format (1-2)", choices=["1", "2"])
    download_type = "video" if format_choice == "1" else "audio"

    success, out_dir = downloader.download_playlist(url, download_type=download_type)
    if success:
        console.print(f"[bold green]✨ Playlist finished downloading to: {out_dir}[/bold green]")
    else:
        console.print("[bold red]⚠️ Playlist finished with some errors or skipped items.[/bold red]")

    ask_string("Press Enter to return to main menu...", allow_empty=True)
