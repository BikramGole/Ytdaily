"""
Help and reference screen for Ytdaily.
"""

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_string


def show_help_screen() -> None:
    """Render the help and user guide screen."""
    console.print("")
    console.print(Rule("[bold cyan]❓ Ytdaily Guide & Shortcuts[/bold cyan]"))
    console.print("")

    shortcuts_table = Table(title="[bold yellow]Keyboard & Option Shortcuts[/bold yellow]", box=box.ROUNDED)
    shortcuts_table.add_column("Key / Shortcut", style="bold cyan", width=16)
    shortcuts_table.add_column("Action", style="white")

    shortcuts_table.add_row("1 - 9", "Select corresponding numbered menu option")
    shortcuts_table.add_row("c", "Quick shortcut to clear resume cache")
    shortcuts_table.add_row("h or ?", "Display this help screen")
    shortcuts_table.add_row("0 or q", "Back to previous screen or exit application")
    shortcuts_table.add_row("Ctrl + C", "Graceful interrupt of ongoing download or scan")

    console.print(shortcuts_table)
    console.print("")

    info_text = (
        "[bold green]1. Silent Automation Engine[/bold green]\n"
        "• Automatic runs (option 1) scan your monitored channels and playlists.\n"
        "• It only downloads videos you haven't downloaded before (gap-based tracking).\n"
        "• All downloads run in multi-threaded parallel queues for maximum speed.\n\n"
        "[bold green]2. SponsorBlock Integration[/bold green]\n"
        "• Automatically scrubs non-content segments: sponsors, intros, outros, and self-promos.\n\n"
        "[bold green]3. Cookie Authentication[/bold green]\n"
        "• Automatically extracts session cookies from your installed browser (Brave, Chrome, Firefox, etc.)\n"
        "  to avoid YouTube bot detection and rate limits.\n\n"
        "[bold green]4. Systemd Background Automation[/bold green]\n"
        "• Check status anytime: [bold cyan]systemctl --user status ytdaily.timer[/bold cyan]\n"
        "• Runs silently once daily with lowest process priority (idle IO) so your computer never lags."
    )

    console.print(Panel(info_text, title="[bold blue]Feature Architecture[/bold blue]", border_style="blue", box=box.ROUNDED))
    console.print("")

    ask_string("Press Enter to return to main menu...", allow_empty=True)
