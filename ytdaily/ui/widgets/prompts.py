"""
Styled Rich Prompt helpers with validation and range checking.
"""

from typing import List, Optional, Sequence
from rich.prompt import Prompt, IntPrompt, Confirm
from ytdaily.theme import console


def ask_choice(
    prompt_text: str,
    choices: Sequence[str],
    default: Optional[str] = None,
    show_choices: bool = True,
) -> str:
    """Prompt user for a choice with validation."""
    try:
        res = Prompt.ask(
            f"[bold cyan]{prompt_text}[/bold cyan]",
            choices=list(choices),
            default=default,
            show_choices=show_choices,
            console=console,
        )
        return str(res or default or "").strip()
    except EOFError:
        return "0"


def ask_string(
    prompt_text: str,
    default: Optional[str] = None,
    allow_empty: bool = False,
) -> str:
    """Prompt user for text with optional default and empty checks."""
    while True:
        try:
            res = Prompt.ask(
                f"[bold cyan]{prompt_text}[/bold cyan]",
                default=default or ("" if allow_empty else None),
                console=console,
            )
            val = str(res if res is not None else (default or "")).strip()
            if val or allow_empty:
                return val
            console.print("[bold red]❌ Input cannot be empty. Please try again.[/bold red]")
        except EOFError:
            return default or ""


def ask_int(
    prompt_text: str,
    default: Optional[int] = None,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
) -> int:
    """Prompt user for an integer within an optional range [min_val, max_val]."""
    range_hint = ""
    if min_val is not None and max_val is not None:
        range_hint = f" ({min_val}-{max_val})"
    elif min_val is not None:
        range_hint = f" (>= {min_val})"
    elif max_val is not None:
        range_hint = f" (<= {max_val})"

    while True:
        try:
            val = IntPrompt.ask(
                f"[bold cyan]{prompt_text}{range_hint}[/bold cyan]",
                default=default,
                console=console,
            )
            if min_val is not None and val < min_val:
                console.print(f"[bold red]❌ Value must be at least {min_val}.[/bold red]")
                continue
            if max_val is not None and val > max_val:
                console.print(f"[bold red]❌ Value must be at most {max_val}.[/bold red]")
                continue
            return val
        except (ValueError, TypeError):
            console.print("[bold red]❌ Please enter a valid integer number.[/bold red]")
        except EOFError:
            return default if default is not None else (min_val or 0)


def ask_confirm(prompt_text: str, default: bool = True) -> bool:
    """Prompt user for a yes/no confirmation dialog."""
    try:
        return Confirm.ask(
            f"[bold yellow]{prompt_text}[/bold yellow]",
            default=default,
            console=console,
        )
    except EOFError:
        return default
