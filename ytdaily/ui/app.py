"""
Main application loop and controller for Ytdaily.
"""

import time
from pathlib import Path
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.tree import Tree
from rich import box

from ytdaily.config import Config
from ytdaily.core.downloader import Downloader
from ytdaily.core.scanner import Scanner
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.screens.channels import manage_channels
from ytdaily.ui.screens.help import show_help_screen
from ytdaily.ui.screens.history import show_history_screen
from ytdaily.ui.screens.main_menu import show_main_menu
from ytdaily.ui.screens.playlists import manage_playlists
from ytdaily.ui.screens.settings import manage_settings
from ytdaily.ui.screens.single_download import (
    download_single_video_interactive,
    download_single_audio_interactive,
    download_playlist_interactive,
)
from ytdaily.ui.screens.statistics import show_statistics
from ytdaily.ui.widgets.prompts import ask_confirm, ask_int, ask_string
from ytdaily.ui.widgets.tables import create_summary_table
from ytdaily.utils.cache import calculate_directory_duration, rename_directory_with_duration
from ytdaily.utils.logging import setup_logging
from ytdaily.utils.notifications import send_notification


class YtdailyApp:
    """Main application controller linking UI screens with core logic."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(config.app_log_path, config.max_log_size, config.max_log_files)
        self.state = StateManager(config, logger=self.logger)
        self.scanner = Scanner(config, self.state, logger=self.logger)
        self.downloader = Downloader(config, self.state, self.scanner, logger=self.logger)

        self.ensure_current_directories()

    def ensure_current_directories(self) -> None:
        """Ensure current directories exist, stripping duration suffixes if present."""
        video_parent = self.config.base_video_dir.parent
        renamed_dirs = list(video_parent.glob("YT_feed -*"))
        if renamed_dirs:
            latest_dir = max(renamed_dirs, key=lambda x: x.stat().st_mtime)
            if not self.config.base_video_dir.exists():
                try:
                    latest_dir.rename(self.config.base_video_dir)
                    self.logger.info(f"📁 Renamed {latest_dir.name} back to {self.config.base_video_dir.name}")
                except OSError as e:
                    self.logger.error(f"❌ Error renaming directory: {e}")

        self.config.current_video_dir.mkdir(parents=True, exist_ok=True)
        self.config.current_audio_dir.mkdir(parents=True, exist_ok=True)
        self.config.current_playlist_dir.mkdir(parents=True, exist_ok=True)
        self.config.current_podcast_dir.mkdir(parents=True, exist_ok=True)

    def update_directory_names(self) -> None:
        """Update YT_feed and playlist directories with calculated media duration."""
        console.print(Rule("[bold magenta]Calculating Media Durations[/bold magenta]"))
        console.print("")

        tree = Tree("📁 [bold]Directories[/bold]")
        with console.status("[bold green]Scanning media files for durations...[/bold green]"):
            current_video_dir = self.config.current_video_dir
            if current_video_dir.exists():
                v_seconds, v_duration, _ = calculate_directory_duration(current_video_dir, self.config.duration_cache)
                if v_seconds > 0:
                    tree.add(f"📁 [yellow]YT_feed -{v_duration}[/yellow]")
                else:
                    tree.add("📁 [yellow]YT_feed[/yellow]")

            current_playlist_dir = self.config.current_playlist_dir
            if current_playlist_dir.exists():
                p_seconds, p_dur, _ = calculate_directory_duration(current_playlist_dir, self.config.duration_cache)
                if p_seconds > 0:
                    playlist_node = tree.add(f"📚 [blue]YT_playlist (combined) - {p_dur}[/blue]")
                    for p_dir in [d for d in current_playlist_dir.iterdir() if d.is_dir()]:
                        new_p_dir, item_sec, item_dur = rename_directory_with_duration(
                            p_dir, p_dir.name, self.config.duration_cache
                        )
                        if item_sec > 0:
                            playlist_node.add(f"📚 {new_p_dir.name}")

        console.print(tree)
        console.print("")

    def run_auto_download(self) -> None:
        """Execute the automatic background or CLI download workflow."""
        start_time = time.time()
        self.downloader.cleanup_old_videos()

        console.print("")
        console.print(Rule("[bold blue]🚀 Starting Ytdaily Auto Download Engine[/bold blue]"))
        console.print("")

        # Overview panel
        stats_text = Text()
        stats_text.append(f"📁 Videos: {self.config.current_video_dir}\n", style="yellow")
        stats_text.append(f"🎧 Audio: {self.config.current_audio_dir}\n", style="yellow")
        stats_text.append(f"👀 Monitoring: {len(self.state.channels)} channels, {len(self.state.playlists)} playlists\n", style="green")
        stats_text.append(f"⚡ Parallel: {self.config.max_parallel_downloads} simultaneous streams\n", style="bold")
        stats_text.append(f"🔄 Resume: Enabled ({self.config.resume_cache_days} days)\n")
        stats_text.append(f"🧹 Auto-cleanup: {self.config.cleanup_days} days\n")
        if self.config.filter_shorts:
            stats_text.append("⏱️  Shorts Filter: Enabled (<60s skipped)", style="green")

        console.print(Panel(stats_text, title="[bold blue]Run Configuration[/bold blue]", border_style="blue", box=box.ROUNDED))
        console.print("")

        all_download_tasks = []

        if self.state.is_first_run():
            console.print("[bold yellow]📺 First run detected: Downloading initial videos[/bold yellow]")
            video_limit = self.config.initial_videos_per_channel
            if self.config.ask_initial_videos and console.is_terminal:
                video_limit = ask_int(
                    "How many RECENT videos to download per source on first run?",
                    default=self.config.initial_videos_per_channel,
                    min_val=0,
                    max_val=self.config.max_videos_per_channel,
                )

            if self.state.channels:
                console.print(Rule("[bold blue]Checking Channels[/bold blue]"))
                for handle, name in self.state.channels.items():
                    tasks = self.scanner.process_channel_first_run(handle, name, video_limit, item_type="channel")
                    all_download_tasks.extend(tasks)

            if self.state.playlists:
                console.print(Rule("[bold blue]Checking Playlists[/bold blue]"))
                for url, name in self.state.playlists.items():
                    tasks = self.scanner.process_channel_first_run(url, name, video_limit, item_type="playlist")
                    all_download_tasks.extend(tasks)

            self.state.mark_first_run_completed()
        else:
            console.print(Rule("[bold green]Checking for NEW Videos[/bold green]"))
            console.print("")

            if self.state.channels:
                for handle, name in self.state.channels.items():
                    tasks = self.scanner.process_channel_auto(handle, name)
                    all_download_tasks.extend(tasks)

            if self.state.playlists:
                console.print(Rule("[bold blue]Checking Playlists[/bold blue]"))
                for url, name in self.state.playlists.items():
                    tasks = self.scanner.process_playlist_auto(url, name)
                    all_download_tasks.extend(tasks)

        successful_downloads = self.downloader.download_videos_parallel(all_download_tasks)
        elapsed = time.time() - start_time

        self.downloader.cleanup_empty_directories()
        self.update_directory_names()

        console.print(create_summary_table(successful_downloads, elapsed))
        console.print("")

        if successful_downloads > 0:
            send_notification(
                "Downloads Complete",
                f"Downloaded {successful_downloads} new videos in {elapsed:.1f}s",
            )
        elif elapsed > 60:
            send_notification("Check Complete", "No new videos found")

    def clear_all_resume_data(self) -> None:
        """Clear resume state with user confirmation."""
        confirmed = ask_confirm("Are you sure you want to clear all resume cache data?", default=False)
        if confirmed:
            self.state.clear_all_resume_data()
            console.print("[bold green]✅ All resume data cleared successfully![/bold green]")
        else:
            console.print("[dim]Cancelled clearing resume data.[/dim]")
        ask_string("Press Enter to return...", allow_empty=True)

    def interactive_mode(self) -> None:
        """Interactive loop providing unified Rich screens."""
        while True:
            choice = show_main_menu(self.config, self.state)

            if choice == "1":
                self.run_auto_download()
                ask_string("Press Enter to return to main menu...", allow_empty=True)
            elif choice == "2":
                manage_channels(self.state)
            elif choice == "3":
                manage_playlists(self.state)
            elif choice == "4":
                download_single_video_interactive(self.downloader, self.scanner)
            elif choice == "5":
                download_single_audio_interactive(self.downloader, self.scanner)
            elif choice == "6":
                download_playlist_interactive(self.downloader, self.scanner, self.config)
            elif choice == "7":
                show_statistics(self.config, self.state)
            elif choice == "8":
                show_history_screen(self.state)
            elif choice == "9":
                manage_settings(self.config, self.state)
            elif choice == "c":
                self.clear_all_resume_data()
            elif choice == "h":
                show_help_screen()
            elif choice == "0":
                console.print("\n[bold cyan]👋 Goodbye from Ytdaily![/bold cyan]\n")
                break
