"""
Unified Rich Progress widget factories for single, playlist, and parallel downloads.
"""

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from ytdaily.theme import console


def create_single_progress() -> Progress:
    """Create a Progress widget for single video or audio downloads."""
    return Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("{task.description}"),
        BarColumn(bar_width=35, style="dim white", complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[cyan]{task.fields[speed]:>10}[/cyan]"),
        TextColumn("[yellow]{task.fields[eta]:>6}[/yellow]"),
        console=console,
        transient=False,
    )


def create_playlist_progress() -> Progress:
    """Create a dual-capable Progress widget for playlist downloads."""
    return Progress(
        SpinnerColumn(spinner_name="bouncingBar"),
        TextColumn("{task.description}"),
        BarColumn(bar_width=35, style="dim blue", complete_style="bold blue"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[cyan]{task.fields[speed]:>10}[/cyan]"),
        TextColumn("[yellow]{task.fields[eta]:>6}[/yellow]"),
        console=console,
        transient=False,
    )


def create_parallel_progress() -> Progress:
    """Create a multi-bar Progress widget for parallel background downloads."""
    return Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold blue]{task.fields[source]}", justify="right"),
        TextColumn("[white]{task.description}"),
        BarColumn(bar_width=None, style="dim white", complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[cyan]{task.fields[speed]:>10}[/cyan]", justify="right"),
        TextColumn("[yellow]{task.fields[eta]:>6}[/yellow]", justify="right"),
        console=console,
        expand=True,
    )
