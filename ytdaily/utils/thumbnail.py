"""
Terminal and GUI thumbnail rendering utilities.
Supports Kitty Graphics Protocol, WezTerm (iTerm2 protocol), and 24-bit ANSI half-block fallbacks.
Calculates terminal dimensions to ensure accurate aspect ratios for landscape, portrait, and square media.
"""

import base64
import io
import os
import shutil
import sys
import urllib.request
from typing import Optional, Tuple

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


def calculate_terminal_dimensions(
    img_width: int,
    img_height: int,
    term_cols: Optional[int] = None,
    term_lines: Optional[int] = None,
) -> Tuple[int, int]:
    """Calculate terminal columns and rows preserving the image's aspect ratio.

    Accounts for standard monospace font cell aspect ratio (~1:2 width:height).
    Limits height to 10-11 rows so preview thumbnails fit cleanly on standard 24-line terminals.
    """
    if not term_cols or not term_lines:
        size = shutil.get_terminal_size((80, 24))
        term_cols = term_cols or size.columns
        term_lines = term_lines or size.lines

    # Bound maximum thumbnail size relative to terminal screen
    max_cols = min(40, max(20, term_cols // 2))
    max_rows = min(11, max(8, term_lines // 2 - 1))

    # Cell width is ~0.5 of cell height (1:2).
    # rows = cols * (img_height / (2.0 * img_width))
    cols = max_cols
    rows = max(1, round(cols * (img_height / (2.0 * img_width))))
    if rows > max_rows:
        rows = max_rows
        cols = max(2, round(rows * (2.0 * img_width) / img_height))

    if cols % 2 != 0:
        cols += 1

    return max(4, cols), max(2, rows)


def is_kitty() -> bool:
    """Check if the current terminal is Kitty."""
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return (
        "kitty" in term
        or "kitty" in term_program
        or "KITTY_PID" in os.environ
        or "KITTY_WINDOW_ID" in os.environ
    )


def is_wezterm() -> bool:
    """Check if the current terminal is WezTerm."""
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return (
        "wezterm" in term_program
        or "WEZTERM_PANE" in os.environ
        or "WEZTERM_EXECUTABLE" in os.environ
        or "WEZTERM_UNIX_SOCKET" in os.environ
    )


def is_iterm2() -> bool:
    """Check if the current terminal supports the iTerm2 inline image protocol."""
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return "iterm" in term_program or "ghostty" in term_program or is_wezterm()


def is_kitty_or_wezterm() -> bool:
    """Kept for backward compatibility."""
    return is_kitty() or is_wezterm()


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


def render_kitty_graphics(png_bytes: bytes, cols: int = 40, rows: Optional[int] = None) -> str:
    """Format PNG bytes into Kitty Graphics Protocol escape sequences with exact cell bounds."""
    b64_data = base64.b64encode(png_bytes).decode("ascii")
    chunk_size = 4096
    chunks = [b64_data[i:i + chunk_size] for i in range(0, len(b64_data), chunk_size)]
    res = ["  "]
    for i, chunk in enumerate(chunks):
        is_first = (i == 0)
        is_last = (i == len(chunks) - 1)
        m = 0 if is_last else 1
        if is_first:
            dim = f"c={cols},r={rows}" if rows else f"c={cols}"
            header = f"a=T,f=100,{dim},m={m}"
        else:
            header = f"m={m}"
        res.append(f"\033_G{header};{chunk}\033\\")
    res.append("\n")
    return "".join(res)


def render_iterm2_graphics(png_bytes: bytes, cols: int = 40, rows: Optional[int] = None) -> str:
    """Format PNG bytes into iTerm2/WezTerm inline image escape sequences."""
    b64_data = base64.b64encode(png_bytes).decode("ascii")
    height_param = f";height={rows}" if rows else ";height=auto"
    return f"  \033]1337;File=inline=1;width={cols}{height_param};preserveAspectRatio=1:{b64_data}\a\n"


def render_halfblocks_ansi(
    image_bytes: bytes,
    cols: int = 40,
    rows: int = 11,
    indent: int = 2,
) -> str:
    """Render image bytes as 24-bit truecolor Unicode half-blocks with exact aspect ratio."""
    if Image is None:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        target_width = cols
        target_height = rows * 2  # 2 vertical pixels per cell

        resized = img.convert("RGB").resize((target_width, target_height), Image.Resampling.BILINEAR)
        pixels = resized.load()

        pad = " " * indent
        lines = []
        for y in range(0, target_height, 2):
            line = [pad]
            for x in range(target_width):
                r1, g1, b1 = pixels[x, y]
                r2, g2, b2 = pixels[x, y + 1] if y + 1 < target_height else (0, 0, 0)
                line.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀")
            line.append("\033[0m")
            lines.append("".join(line))
        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def display_terminal_thumbnail(thumbnail_url: str) -> bool:
    """Download and display a video thumbnail with proper aspect ratio across Kitty, WezTerm, iTerm2, and ANSI."""
    data = download_thumbnail_bytes(thumbnail_url)
    if not data:
        return False

    w, h = 16, 9
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(data))
            w, h = img.size
        except Exception:
            pass

    cols, rows = calculate_terminal_dimensions(w, h)
    png_data = to_png_bytes(data, max_width=400)

    try:
        # WezTerm has native, rock-solid support for iTerm2 protocol with preserveAspectRatio=1
        if (is_wezterm() or is_iterm2()) and png_data:
            sys.stdout.write(render_iterm2_graphics(png_data, cols=cols, rows=rows))
            sys.stdout.flush()
            return True
        elif is_kitty() and png_data:
            sys.stdout.write(render_kitty_graphics(png_data, cols=cols, rows=rows))
            sys.stdout.flush()
            return True
        elif Image is not None:
            ansi = render_halfblocks_ansi(data, cols=cols, rows=rows)
            if ansi:
                sys.stdout.write(ansi)
                sys.stdout.flush()
                return True
    except Exception:
        pass

    return False
