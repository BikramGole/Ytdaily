"""
Reusable Rich Table builders for Ytdaily.
"""

from typing import Dict, List, Any
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from ytdaily.config import Config
from ytdaily.core.state import StateManager
from ytdaily.utils.system import get_disk_space_info


def create_item_table(
    title: str,
    items_dict: Dict[str, str],
    item_type: str = "Channel",
    filter_query: str = "",
) -> Table:
    """Build a styled table listing channels or playlists with index."""
    table = Table(
        title=f"[bold blue]{title}[/bold blue]",
        box=box.ROUNDED,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("#", style="dim", justify="right", width=4)
    table.add_column("Display Name", style="bold white")
    table.add_column(f"{item_type} Identifier / URL", style="cyan", overflow="ellipsis")

    idx = 1
    query = filter_query.lower()
    for key, name in items_dict.items():
        if query and query not in name.lower() and query not in key.lower():
            continue
        table.add_row(str(idx), name, key)
        idx += 1

    if idx == 1:
        empty_msg = f"No {item_type.lower()}s match the search query." if query else f"No {item_type.lower()}s configured yet."
        table.add_row("-", f"[dim]{empty_msg}[/dim]", "-")

    return table


def create_summary_table(successful_downloads: int, elapsed: float) -> Table:
    """Build download summary report table."""
    table = Table(
        title="[bold green]Download Summary Report[/bold green]",
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("New Downloads", str(successful_downloads))
    table.add_row("Total Time", f"{elapsed:.1f}s")
    if successful_downloads > 0:
        table.add_row("Avg Time/Download", f"{elapsed / successful_downloads:.1f}s")
    return table


def create_history_table(history_items: List[Dict[str, Any]]) -> Table:
    """Build download history table."""
    table = Table(
        title="[bold magenta]Recent Download History[/bold magenta]",
        box=box.ROUNDED,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("#", style="dim", justify="right", width=4)
    table.add_column("Date", style="dim cyan", width=19)
    table.add_column("Source", style="bold yellow", width=22, overflow="ellipsis")
    table.add_column("Title", style="white", overflow="ellipsis")
    table.add_column("ID", style="cyan", width=13)

    if not history_items:
        table.add_row("-", "-", "-", "[dim]No download history found.[/dim]", "-")
        return table

    for i, item in enumerate(history_items, 1):
        dt_str = item.get("downloaded_at", "")[:19].replace("T", " ")
        table.add_row(
            str(i),
            dt_str,
            item.get("source", "Unknown"),
            item.get("title", "Unknown"),
            item.get("video_id", ""),
        )

    return table


def create_status_bar(config: Config, state: StateManager) -> Panel:
    """Build a compact system status bar panel for the main menu."""
    disk = get_disk_space_info(config.base_video_dir)
    num_channels = len(state.channels)
    num_playlists = len(state.playlists)
    last_dl = state.get_last_download()

    last_info = "None"
    if last_dl and "title" in last_dl:
        title = last_dl.get("title", "")
        if len(title) > 28:
            title = title[:28] + "…"
        last_info = f"{title} ({last_dl.get('type', 'Video')})"

    browser_disp = config.browser
    if browser_disp == "auto":
        from ytdaily.utils.browser import detect_browser
        browser_disp = f"auto ({detect_browser()})"

    status_text = Text()
    status_text.append("📊 Monitored: ", style="bold")
    status_text.append(f"{num_channels} channels, {num_playlists} playlists   ", style="green")

    status_text.append("💾 Disk Free: ", style="bold")
    free_color = "green" if disk.get("free_raw_gb", 0) > 10 else "yellow" if disk.get("free_raw_gb", 0) > 3 else "bold red"
    status_text.append(f"{disk.get('free_gb', 'N/A')} ({disk.get('used_percent', 'N/A')} used)   ", style=free_color)

    status_text.append("🍪 Cookies: ", style="bold")
    status_text.append(f"{browser_disp}\n", style="cyan")

    status_text.append("🕒 Last Download: ", style="bold")
    status_text.append(f"{last_info}   ", style="dim white")

    status_text.append("🧹 Auto-cleanup: ", style="bold")
    status_text.append(f"{config.cleanup_days} days   ", style="yellow")

    status_text.append("⚡ Parallel: ", style="bold")
    status_text.append(f"{config.max_parallel_downloads}", style="magenta")

    return Panel(
        status_text,
        title="[bold blue]System Status[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
    )
