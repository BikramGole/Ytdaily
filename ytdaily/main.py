"""
Entry point for Ytdaily CLI and Interactive application.
"""

import argparse
import sys
from rich.panel import Panel
from ytdaily import __version__
from ytdaily.config import Config
from ytdaily.theme import console
from ytdaily.ui.app import YtdailyApp
from ytdaily.utils.system import check_dependencies


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Ytdaily — Interactive and Automated YouTube Feed Downloader",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start in interactive Rich TUI mode",
    )
    parser.add_argument(
        "--auto", "-a",
        action="store_true",
        help="Run auto-download directly without interactive prompt",
    )
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Start the desktop application (Windows, Linux, and macOS)",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"Ytdaily {__version__}",
    )
    args = parser.parse_args()

    if args.gui:
        try:
            from ytdaily.gui.main import main as gui_main
        except ImportError as error:
            console.print(
                "[bold red]Desktop GUI dependencies are missing.[/bold red] "
                "Run [cyan]pip install -r requirements.txt[/cyan] and try again."
            )
            raise SystemExit(1) from error
        raise SystemExit(gui_main())

    ok, missing = check_dependencies()
    if not ok:
        missing_list = "\n".join(f"  • [bold cyan]{m}[/bold cyan]" for m in missing)
        instructions = (
            f"[bold red]❌ Required dependencies missing:[/bold red]\n\n"
            f"{missing_list}\n\n"
            "[yellow]Please install using your distribution's package manager:[/yellow]\n"
            "  • [bold white]Arch Linux:[/bold white] sudo pacman -S yt-dlp ffmpeg\n"
            "  • [bold white]Debian/Ubuntu:[/bold white] sudo apt-get install yt-dlp ffmpeg\n"
            "  • [bold white]Fedora:[/bold white] sudo dnf install yt-dlp ffmpeg"
        )
        console.print(Panel(instructions, title="[bold red]Missing System Tools[/bold red]", border_style="red"))
        sys.exit(1)

    config = Config()
    app = YtdailyApp(config)

    try:
        if args.interactive:
            app.interactive_mode()
        else:
            app.run_auto_download()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]⚠️ Operation cancelled by user.[/bold yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal error:[/bold red] {e}\n")
        app.logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
