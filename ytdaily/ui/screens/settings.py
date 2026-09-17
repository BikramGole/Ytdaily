"""
Settings screen with input validation, range checks, and configurable directories.
"""

from pathlib import Path
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box
from ytdaily.config import Config, SUPPORTED_RESOLUTIONS
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_choice, ask_int, ask_string
from ytdaily.utils.browser import SUPPORTED_BROWSERS, detect_browser


def manage_settings(config: Config, state: StateManager) -> None:
    """Settings management screen with range validation and retry loops."""
    while True:
        console.print("")
        console.print(Rule("[bold cyan]⚙️ Application Settings[/bold cyan]"))
        console.print("")

        browser_disp = config.browser
        if browser_disp == "auto":
            detected = detect_browser()
            browser_disp = f"auto (detected: {detected})"

        table = Table(
            title="[bold blue]Current Configuration[/bold blue]",
            box=box.ROUNDED,
            header_style="bold magenta",
        )
        table.add_column("#", style="dim", justify="right", width=4)
        table.add_column("Setting Name", style="bold white")
        table.add_column("Current Value", style="cyan")
        table.add_column("Allowed Range / Options", style="dim")

        table.add_row("1", "⚡ Parallel Downloads", str(config.max_parallel_downloads), "1 - 10")
        table.add_row("2", "🗑️ Resume Cache Days", f"{config.resume_cache_days} days", "1 - 365")
        table.add_row("3", "🔔 Ask for recent on first run", "ENABLED" if config.ask_initial_videos else "DISABLED", "Toggle")
        table.add_row("4", "📺 First-run download count", str(config.initial_videos_per_channel), f"0 - {config.max_videos_per_channel}")
        table.add_row("5", "📊 Max videos to check/channel", str(config.max_videos_per_channel), "1 - 200")
        table.add_row("6", "🎥 Max Video Quality", f"{config.max_resolution}p", ", ".join(SUPPORTED_RESOLUTIONS))
        table.add_row("7", "🍪 Browser for cookies", browser_disp, "auto, " + ", ".join(SUPPORTED_BROWSERS) + ", none")
        table.add_row("8", "📁 Video Directory", str(config.base_video_dir), "Valid directory path")
        table.add_row("9", "🎧 Audio Directory", str(config.base_audio_dir), "Valid directory path")
        table.add_row("10", "🧹 Video Retention Days", f"{config.cleanup_days} days", "1 - 3650")
        table.add_row("11", "⏱️ Filter Shorts (<60s)", "ENABLED" if config.filter_shorts else "DISABLED", "Toggle")

        console.print(table)
        console.print("")

        choice = ask_choice(
            "Select setting to modify (1-11, 0 to back)",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "0", "q", "b"],
            show_choices=False,
        )

        if choice in ("0", "q", "b"):
            state.save_config()
            break

        elif choice == "1":
            config.max_parallel_downloads = ask_int(
                "Enter parallel downloads count",
                default=config.max_parallel_downloads,
                min_val=1,
                max_val=10,
            )
            state.save_config()
            console.print(f"[bold green]✅ Parallel downloads set to: {config.max_parallel_downloads}[/bold green]")

        elif choice == "2":
            config.resume_cache_days = ask_int(
                "Enter resume cache retention days",
                default=config.resume_cache_days,
                min_val=1,
                max_val=365,
            )
            state.cleanup_old_resume_entries()
            state.save_config()
            console.print(f"[bold green]✅ Resume cache days set to: {config.resume_cache_days}[/bold green]")

        elif choice == "3":
            config.ask_initial_videos = not config.ask_initial_videos
            status = "ENABLED" if config.ask_initial_videos else "DISABLED"
            state.save_config()
            console.print(f"[bold green]✅ Ask for recent videos on first run: {status}[/bold green]")

        elif choice == "4":
            config.initial_videos_per_channel = ask_int(
                "Enter auto-download recent videos count on first run",
                default=config.initial_videos_per_channel,
                min_val=0,
                max_val=config.max_videos_per_channel,
            )
            state.save_config()
            console.print(f"[bold green]✅ First-run video count set to: {config.initial_videos_per_channel}[/bold green]")

        elif choice == "5":
            config.max_videos_per_channel = ask_int(
                "Enter max videos to check per channel",
                default=config.max_videos_per_channel,
                min_val=1,
                max_val=200,
            )
            state.save_config()
            console.print(f"[bold green]✅ Max videos per channel set to: {config.max_videos_per_channel}[/bold green]")

        elif choice == "6":
            console.print(f"[bold cyan]Available resolutions:[/bold cyan] {', '.join(SUPPORTED_RESOLUTIONS)}")
            config.max_resolution = ask_choice(
                "Select max resolution",
                choices=SUPPORTED_RESOLUTIONS,
                default=config.max_resolution,
            )
            state.save_config()
            console.print(f"[bold green]✅ Max resolution set to: {config.max_resolution}p[/bold green]")

        elif choice == "7":
            valid_browsers = ["auto", "none"] + list(SUPPORTED_BROWSERS)
            console.print(f"[bold cyan]Available options:[/bold cyan] {', '.join(valid_browsers)}")
            config.browser = ask_choice(
                "Select cookie browser",
                choices=valid_browsers,
                default=config.browser,
            )
            state.save_config()
            console.print(f"[bold green]✅ Browser set to: {config.browser}[/bold green]")

        elif choice == "8":
            new_path_str = ask_string("Enter new video directory path:", default=str(config.base_video_dir))
            new_path = Path(new_path_str).expanduser().resolve()
            try:
                new_path.mkdir(parents=True, exist_ok=True)
                config.base_video_dir = new_path
                state.save_config()
                console.print(f"[bold green]✅ Video directory updated to: {new_path}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]❌ Invalid directory path: {e}[/bold red]")

        elif choice == "9":
            new_path_str = ask_string("Enter new audio directory path:", default=str(config.base_audio_dir))
            new_path = Path(new_path_str).expanduser().resolve()
            try:
                new_path.mkdir(parents=True, exist_ok=True)
                config.base_audio_dir = new_path
                state.save_config()
                console.print(f"[bold green]✅ Audio directory updated to: {new_path}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]❌ Invalid directory path: {e}[/bold red]")

        elif choice == "10":
            config.cleanup_days = ask_int(
                "Enter video retention days",
                default=config.cleanup_days,
                min_val=1,
                max_val=3650,
            )
            state.save_config()
            console.print(f"[bold green]✅ Retention days set to: {config.cleanup_days}[/bold green]")

        elif choice == "11":
            config.filter_shorts = not config.filter_shorts
            status = "ENABLED" if config.filter_shorts else "DISABLED"
            state.save_config()
            console.print(f"[bold green]✅ Shorts filter: {status}[/bold green]")
