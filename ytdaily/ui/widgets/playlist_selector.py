"""Keyboard-driven playlist item selector for the interactive CLI."""

import os
import select
import sys
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional, Sequence, Set

from rich import box
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ytdaily.theme import console


def selected_playlist_indices(videos: Sequence[dict[str, Any]], selected: Set[int]) -> List[int]:
    """Return selected yt-dlp playlist positions in playlist order."""
    return [
        int(video.get("playlist_index", index))
        for index, video in enumerate(videos, start=1)
        if index in selected
    ]


@contextmanager
def _raw_keyboard() -> Iterator[None]:
    """Read one key at a time without adding a third-party TUI dependency."""
    if not sys.stdin.isatty():
        yield
        return
    if os.name == "nt":
        yield
        return

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _read_key() -> str:
    """Read a normalized key name, including common terminal arrow sequences."""
    if os.name == "nt":
        import msvcrt

        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        return {"\r": "enter", "\t": "tab", " ": "space", "\x1b": "escape", "\x08": "backspace"}.get(key, key)

    key = sys.stdin.read(1)
    if key != "\x1b":
        return {"\r": "enter", "\n": "enter", "\t": "tab", " ": "space", "\x7f": "backspace"}.get(key, key)

    ready, _, _ = select.select([sys.stdin], [], [], 0.05)
    if not ready:
        return "escape"
    if sys.stdin.read(1) != "[":
        return "escape"
    ready, _, _ = select.select([sys.stdin], [], [], 0.05)
    if not ready:
        return "escape"
    return {"A": "up", "B": "down"}.get(sys.stdin.read(1), "")


def _selector_view(videos: Sequence[dict[str, Any]], selected: Set[int], cursor: int) -> Panel:
    """Create a compact, scrollable Rich view for the current selector state."""
    visible_rows = max(5, (console.size.height or 24) - 10)
    start = min(max(0, cursor - visible_rows // 2), max(0, len(videos) - visible_rows))
    end = min(len(videos), start + visible_rows)

    table = Table(box=box.SIMPLE, expand=True, show_header=False, padding=(0, 1))
    table.add_column("Selected", width=3)
    table.add_column("Video", overflow="ellipsis")
    table.add_column("Length", justify="right", width=8)
    for index in range(start, end):
        video = videos[index]
        marker = "[green]✓[/green]" if index + 1 in selected else "[dim]○[/dim]"
        title = str(video.get("title", "Untitled"))
        title = f"[reverse]› {index + 1}. {title}[/reverse]" if index == cursor else f"  {index + 1}. {title}"
        table.add_row(marker, title, str(video.get("duration_formatted", "")))

    suffix = f"  Showing {start + 1}–{end} of {len(videos)}." if start > 0 or end < len(videos) else ""
    instructions = (
        f"[bold]{len(selected)} of {len(videos)} selected.[/] "
        "[cyan]↑/↓[/] move · [cyan]Space/Tab[/] toggle · [cyan]Enter[/] confirm · "
        "[cyan]Esc/Backspace[/] go back"
        f"[dim]{suffix}[/dim]"
    )
    return Panel(table, title="[bold blue]Choose playlist videos[/bold blue]", subtitle=instructions, border_style="blue")


def select_playlist_videos(videos: Sequence[dict[str, Any]]) -> Optional[List[int]]:
    """Select playlist entries with arrows and Space/Tab; ``None`` means go back."""
    if not videos:
        console.print("[yellow]No playlist videos were found to select.[/yellow]")
        return []
    if not sys.stdin.isatty() or not console.is_terminal:
        console.print("[yellow]Interactive selection requires a terminal. No videos selected.[/yellow]")
        return []

    selected = set(range(1, len(videos) + 1))
    cursor = 0
    with _raw_keyboard(), Live(_selector_view(videos, selected, cursor), console=console, refresh_per_second=20) as live:
        while True:
            key = _read_key()
            if key == "up":
                cursor = (cursor - 1) % len(videos)
            elif key == "down":
                cursor = (cursor + 1) % len(videos)
            elif key in {"space", "tab"}:
                position = cursor + 1
                if position in selected:
                    selected.remove(position)
                else:
                    selected.add(position)
            elif key == "enter":
                return selected_playlist_indices(videos, selected)
            elif key in {"escape", "backspace", "q", "Q"}:
                return None
            live.update(_selector_view(videos, selected, cursor))
