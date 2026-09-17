"""
Download history viewer screen with search and filtering.
"""

from rich.panel import Panel
from rich.rule import Rule
from rich import box
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_choice, ask_string
from ytdaily.ui.widgets.tables import create_history_table


def show_history_screen(state: StateManager) -> None:
    """Render the download history screen with search/filter capabilities."""
    search_query = ""
    while True:
        console.print("")
        title_suffix = f" (filtered by '{search_query}')" if search_query else ""
        console.print(Rule(f"[bold magenta]📜 Download History Viewer{title_suffix}[/bold magenta]"))
        console.print("")

        items = state.get_all_downloaded_videos(query=search_query if search_query else None, limit=50)
        console.print(create_history_table(items))
        console.print("")

        console.print(
            Panel(
                "1. 📋 [bold]Refresh / Show All[/bold]\n"
                "2. 🔍 [bold]Search History[/bold]\n"
                "0. ↩️  [dim]Back to Main Menu[/dim]",
                title="[bold blue]History Options[/bold blue]",
                border_style="blue",
                box=box.ROUNDED,
            )
        )

        choice = ask_choice("Select option", choices=["1", "2", "0", "q", "b"], show_choices=False)

        if choice in ("0", "q", "b"):
            break
        elif choice == "1":
            search_query = ""
        elif choice == "2":
            search_query = ask_string("Enter search term (title, channel, or video ID):", allow_empty=True)
