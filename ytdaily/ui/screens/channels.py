"""
Channel and playlist management screens using a generic item manager.
"""

from typing import Dict, Callable
from rich.panel import Panel
from rich.rule import Rule
from rich import box
from ytdaily.core.state import StateManager
from ytdaily.theme import console
from ytdaily.ui.widgets.prompts import ask_choice, ask_string, ask_int, ask_confirm
from ytdaily.ui.widgets.tables import create_item_table


def manage_items(
    state: StateManager,
    item_type: str,
    items_dict: Dict[str, str],
    id_label: str,
    id_example: str,
) -> None:
    """Generic item manager for channels and playlists with search and confirmation dialogs."""
    while True:
        console.print("")
        console.print(Rule(f"[bold cyan]📺 {item_type} Management ({len(items_dict)} configured)[/bold cyan]"))
        console.print("")

        console.print(create_item_table(f"Configured {item_type}s", items_dict, item_type=item_type))
        console.print("")

        console.print(
            Panel(
                "1. 📋 [bold]Refresh List[/bold]\n"
                "2. 🔍 [bold]Search / Filter[/bold]\n"
                "3. ➕ [bold]Add {0}[/bold]\n"
                "4. 🗑️  [bold red]Remove {0}[/bold red]\n"
                "0. ↩️  [dim]Back to Main Menu[/dim]".format(item_type),
                title=f"[bold blue]{item_type} Actions[/bold blue]",
                border_style="blue",
                box=box.ROUNDED,
            )
        )

        choice = ask_choice("Select action", choices=["1", "2", "3", "4", "0", "q", "b"], show_choices=False)

        if choice in ("0", "q", "b"):
            break

        elif choice == "1":
            continue

        elif choice == "2":
            query = ask_string(f"Enter search query for {item_type.lower()}:", allow_empty=True)
            console.print("")
            console.print(create_item_table(f"Search Results for '{query}'", items_dict, item_type=item_type, filter_query=query))
            ask_string("Press Enter to return to menu...", allow_empty=True)

        elif choice == "3":
            raw_id = ask_string(f"Enter {id_label} ({id_example}):")
            if item_type.lower() == "channel":
                raw_id = raw_id.lstrip("@").strip()
            name = ask_string(f"Enter {item_type.lower()} display name:")

            if raw_id in items_dict:
                overwrite = ask_confirm(f"'{raw_id}' already exists as '{items_dict[raw_id]}'. Overwrite?", default=True)
                if not overwrite:
                    continue

            items_dict[raw_id] = name
            state.save_config()
            console.print(f"[bold green]✅ Added {item_type.lower()}: {name} ({raw_id})[/bold green]")

        elif choice == "4":
            if not items_dict:
                console.print(f"[bold red]❌ No {item_type.lower()}s to remove.[/bold red]")
                continue

            keys = list(items_dict.keys())
            remove_idx = ask_int(f"Enter number of {item_type.lower()} to remove", min_val=1, max_val=len(keys))
            target_key = keys[remove_idx - 1]
            target_name = items_dict[target_key]

            confirmed = ask_confirm(f"Are you sure you want to remove '{target_name}'?", default=False)
            if confirmed:
                removed_name = items_dict.pop(target_key)
                state.save_config()
                console.print(f"[bold green]✅ Removed {item_type.lower()}: {removed_name}[/bold green]")
            else:
                console.print("[dim]Cancelled removal.[/dim]")


def manage_channels(state: StateManager) -> None:
    """Manage channels screen."""
    manage_items(
        state=state,
        item_type="Channel",
        items_dict=state.channels,
        id_label="channel handle without @",
        id_example="e.g. mreflow or mkbhd",
    )
