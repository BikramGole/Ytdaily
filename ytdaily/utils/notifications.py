"""
Desktop notification support via notify-send.
"""

import subprocess


def send_notification(title: str, message: str, urgency: str = "normal") -> None:
    """Send a desktop notification using notify-send."""
    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-a", "YT Feed", title, message],
            check=False,
            capture_output=True,
        )
    except Exception:
        # Don't crash if notifications fail or notify-send is missing
        pass
