"""
Main Menu screen for Ytdaily.
"""

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box
from ytdaily.config import Config
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_choice
from ytdaily.ui.widgets.tables import create_status_bar


def show_main_menu(config: Config, state: StateManager) -> str:
    """Render the main menu dashboard and prompt for choice."""
    console.print("")
    console.print(Rule("[bold cyan]📺 Ytdaily — YouTube Automation Engine[/bold cyan]", style="blue"))
    console.print("")

    # Status Bar
    console.print(create_status_bar(config, state))
    console.print("")

    # Menu Options Table
    menu_table = Table.grid(padding=(0, 2))
    menu_table.add_column(style="bold yellow", justify="right", width=6)
    menu_table.add_column(style="white")

    menu_table.add_row("[bold green]1[/bold green]", "🚀 [bold green]Run automatic download (SMART mode)[/bold green]")
    menu_table.add_row("2", "📺 Manage channels (add, remove, search)")
    menu_table.add_row("3", "📋 Manage playlists (add, remove, search)")
    menu_table.add_row("4", "🎬 Download single video (with live preview)")
    menu_table.add_row("5", "🎧 Download single audio (320kbps MP3)")
    menu_table.add_row("6", "📚 Download playlist (interactive with dual progress)")
    menu_table.add_row("7", "📊 Show statistics dashboard")
    menu_table.add_row("8", "📜 View download history")
    menu_table.add_row("9", "⚙️  Settings (directory, quality, cookies, limits)")
    menu_table.add_row("c", "🧹 Clear resume data cache")
    menu_table.add_row("h", "❓ Help & shortcuts")
    menu_table.add_row("[bold red]0[/bold red]", "❌ [bold red]Exit[/bold red]")

    console.print(
        Panel(
            menu_table,
            title="[bold blue]Main Menu[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    valid_choices = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "c", "C", "h", "H", "?", "0", "q", "Q"]
    choice = ask_choice("Select option (0-9, c, h)", choices=valid_choices, show_choices=False).lower()

    if choice in ("q", "0"):
        return "0"
    if choice in ("?", "h"):
        return "h"
    return choice
