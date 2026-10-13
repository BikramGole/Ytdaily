import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="YTDaily - YouTube Feed Downloader")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI application")
    parser.add_argument("--tui", action="store_true", help="Launch the TUI application")
    args = parser.parse_args()

    if args.gui:
        from gui.main_window import run_gui
        run_gui()
    elif args.tui:
        from YT_daily import main as tui_main
        tui_main()
    else:
        # Default to GUI if PyQt6 is available, else TUI
        try:
            import PyQt6
            from gui.main_window import run_gui
            run_gui()
        except ImportError:
            from YT_daily import main as tui_main
            tui_main()

if __name__ == "__main__":
    main()
