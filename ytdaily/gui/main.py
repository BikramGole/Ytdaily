"""Windows, Linux, and macOS desktop entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ytdaily.config import Config
from ytdaily.gui.window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Ytdaily")
    app.setOrganizationName("Ytdaily")
    app.setStyle("Fusion")
    window = MainWindow(Config())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
