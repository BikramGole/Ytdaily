"""
Terminal and GUI thumbnail rendering utilities.
Supports Kitty Graphics Protocol, WezTerm, iTerm2, and 24-bit ANSI half-block fallbacks.
"""

import base64
import io
import os
import sys
import urllib.request
from typing import Optional

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


def download_thumbnail_bytes(url: str, timeout: float = 5.0) -> Optional[bytes]:
    """Download image bytes from a URL with browser headers."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def is_kitty_or_wezterm() -> bool:
    """Check if the current terminal supports the Kitty Graphics Protocol."""
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if (
        "kitty" in term
        or "kitty" in term_program
        or "KITTY_PID" in os.environ
        or "KITTY_WINDOW_ID" in os.environ
    ):
        return True
    if (
        "wezterm" in term_program
        or "WEZTERM_PANE" in os.environ
        or "WEZTERM_EXECUTABLE" in os.environ
        or "WEZTERM_UNIX_SOCKET" in os.environ
    ):
        return True
    return False


def is_iterm2() -> bool:
    """Check if the current terminal supports the iTerm2 inline image protocol."""
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return "iterm" in term_program or "ghostty" in term_program


def to_png_bytes(image_bytes: bytes, max_width: int = 400) -> Optional[bytes]:
    """Convert raw image bytes to an optimized PNG byte array."""
    if Image is None:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w > max_width:
            new_h = max(1, int(h * (max_width / w)))
            img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception:
        return None


def render_kitty_graphics(png_bytes: bytes, cols: int = 44) -> str:
    """Format PNG bytes into Kitty Graphics Protocol escape sequences."""
    b64_data = base64.b64encode(png_bytes).decode("ascii")
    chunk_size = 4096
    chunks = [b64_data[i:i + chunk_size] for i in range(0, len(b64_data), chunk_size)]
    res = []
    for i, chunk in enumerate(chunks):
        is_first = (i == 0)
        is_last = (i == len(chunks) - 1)
        m = 0 if is_last else 1
        if is_first:
            header = f"a=T,f=100,c={cols},m={m}"
        else:
            header = f"m={m}"
        res.append(f"\033_G{header};{chunk}\033\\")
    res.append("\n")
    return "".join(res)


def render_iterm2_graphics(png_bytes: bytes, cols: int = 44) -> str:
    """Format PNG bytes into iTerm2 inline image escape sequences."""
    b64_data = base64.b64encode(png_bytes).decode("ascii")
    return f"\033]1337;File=inline=1;width={cols};preserveAspectRatio=1:{b64_data}\a\n"


def render_halfblocks_ansi(image_bytes: bytes, target_cols: int = 44) -> str:
    """Render image bytes as 24-bit truecolor Unicode half-blocks (universal fallback)."""
    if Image is None:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        target_width = target_cols
        target_height = max(2, int(target_width * (h / w)))
        max_height = 36
        if target_height > max_height:
            target_height = max_height
            target_width = max(2, int(target_height * (w / h)))
        if target_height % 2 != 0:
            target_height += 1

        resized = img.convert("RGB").resize((target_width, target_height), Image.Resampling.BILINEAR)
        pixels = resized.load()

        lines = []
        for y in range(0, target_height, 2):
            line = []
            for x in range(target_width):
                r1, g1, b1 = pixels[x, y]
                r2, g2, b2 = pixels[x, y + 1] if y + 1 < target_height else (0, 0, 0)
                line.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀")
            line.append("\033[0m")
            lines.append("".join(line))
        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def display_terminal_thumbnail(thumbnail_url: str, cols: int = 44) -> bool:
    """Download and display a video thumbnail in Kitty, WezTerm, iTerm2, or truecolor ANSI terminals."""
    data = download_thumbnail_bytes(thumbnail_url)
    if not data:
        return False

    is_vertical = False
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(data))
            w, h = img.size
            if h > w:
                is_vertical = True
        except Exception:
            pass

    target_cols = min(cols, 22) if is_vertical else cols
    png_data = to_png_bytes(data, max_width=400)

    try:
        if is_kitty_or_wezterm() and png_data:
            sys.stdout.write(render_kitty_graphics(png_data, cols=target_cols))
            sys.stdout.flush()
            return True
        elif is_iterm2() and png_data:
            sys.stdout.write(render_iterm2_graphics(png_data, cols=target_cols))
            sys.stdout.flush()
            return True
        elif Image is not None:
            ansi = render_halfblocks_ansi(data, target_cols=target_cols)
            if ansi:
                sys.stdout.write(ansi)
                sys.stdout.flush()
                return True
    except Exception:
        pass

    return False
