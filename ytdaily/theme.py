"""
Rich theme and console definitions for Ytdaily.
"""

from rich.console import Console
from rich.theme import Theme
from rich.style import Style

CUSTOM_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "title": "bold blue",
    "highlight": "bold magenta",
    "accent": "bold cyan",
    "muted": "dim",
    "header": "bold magenta",
    "label": "bold white",
    "url": "underline blue",
})

console = Console(theme=CUSTOM_THEME)
