"""Design tokens from prototype.html and the QSS engine that applies them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


def rgba(hex_color: str, alpha_percent: int) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha_percent}%)"


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    crust: str
    mantle: str
    base: str
    surface: str
    surface_high: str
    surface_highest: str
    text_main: str
    text_muted: str
    text_dim: str
    accent: str
    accent_hover: str
    accent_on: str
    success: str
    warning: str
    error: str
    on_error: str
    border: str
    border_subtle: str
    radius_sm: int = 8
    radius_md: int = 16
    font_family: str = '"Segoe UI", "Noto Sans", sans-serif'
    mono_family: str = '"JetBrains Mono", Consolas, monospace'

    @property
    def swatches(self) -> Tuple[str, str, str]:
        return (self.base, self.accent, self.success)


THEMES: Dict[str, Theme] = {
    "catppuccin-mocha": Theme(
        key="catppuccin-mocha",
        name="Catppuccin Mocha",
        crust="#11111b",
        mantle="#181825",
        base="#1e1e2e",
        surface="#313244",
        surface_high="#45475a",
        surface_highest="#585b70",
        text_main="#cdd6f4",
        text_muted="#a6adc8",
        text_dim="#6c7086",
        accent="#cba6f7",
        accent_hover="#d4b8fb",
        accent_on="#11111b",
        success="#a6e3a1",
        warning="#fab387",
        error="#f38ba8",
        on_error="#11111b",
        border="#45475a",
        border_subtle="#313244",
    ),
    "catppuccin-latte": Theme(
        key="catppuccin-latte",
        name="Catppuccin Latte",
        crust="#dce0e8",
        mantle="#e6e9ef",
        base="#eff1f5",
        surface="#ccd0da",
        surface_high="#bcc0cc",
        surface_highest="#acb0be",
        text_main="#4c4f69",
        text_muted="#6c6f85",
        text_dim="#8c8fa1",
        accent="#8839ef",
        accent_hover="#9a51f1",
        accent_on="#eff1f5",
        success="#40a02b",
        warning="#df8e1d",
        error="#d20f39",
        on_error="#ffffff",
        border="#bcc0cc",
        border_subtle="#ccd0da",
    ),
    "material-ui": Theme(
        key="material-ui",
        name="Material UI",
        crust="#0e0e0e",
        mantle="#1a1b1e",
        base="#131314",
        surface="#1e1f20",
        surface_high="#2b2930",
        surface_highest="#36343b",
        text_main="#e3e2e6",
        text_muted="#c4c7c5",
        text_dim="#94979c",
        accent="#a8c7fa",
        accent_hover="#bcd2fb",
        accent_on="#062e6f",
        success="#6dd58c",
        warning="#ffb591",
        error="#f2b8b5",
        on_error="#601410",
        border="#3c4043",
        border_subtle="#2b2930",
        font_family='"Roboto", "Segoe UI", sans-serif',
        mono_family='"Roboto Mono", Consolas, monospace',
    ),
    "windows-11": Theme(
        key="windows-11",
        name="Windows 11 Fluent",
        crust="#191919",
        mantle="#1c1c1c",
        base="#202020",
        surface="#272727",
        surface_high="#323232",
        surface_highest="#3a3a3a",
        text_main="#ffffff",
        text_muted="#cfcfcf",
        text_dim="#9a9a9a",
        accent="#60cdff",
        accent_hover="#7fd6ff",
        accent_on="#002e4a",
        success="#6ccb5f",
        warning="#ffc83d",
        error="#ff99a4",
        on_error="#4a0014",
        border="#3d3d3d",
        border_subtle="#2d2d2d",
        radius_sm=6,
        radius_md=10,
        mono_family='"Cascadia Mono", Consolas, monospace',
    ),
    "monokai": Theme(
        key="monokai",
        name="Monokai Pro",
        crust="#19181a",
        mantle="#222125",
        base="#2d2a2e",
        surface="#363437",
        surface_high="#4a474a",
        surface_highest="#5b585c",
        text_main="#fcfcfa",
        text_muted="#c1c0c0",
        text_dim="#727072",
        accent="#ffd866",
        accent_hover="#ffe07e",
        accent_on="#19181a",
        success="#a9dc76",
        warning="#fc9867",
        error="#ff6188",
        on_error="#19181a",
        border="#4a474a",
        border_subtle="#363437",
        radius_sm=6,
        radius_md=10,
        font_family='"JetBrains Mono", "Fira Code", Consolas, monospace',
        mono_family='"JetBrains Mono", "Fira Code", Consolas, monospace',
    ),
}


def build_stylesheet(theme_key: str) -> str:
    theme = THEMES.get(theme_key) or THEMES["catppuccin-mocha"]
    t = theme
    return f"""
    QMainWindow, QDialog {{ background: {t.crust}; }}
    QWidget {{ color: {t.text_main}; font-family: {t.font_family}; font-size: 13px; }}
    QWidget:disabled {{ color: {t.text_dim}; }}

    QStackedWidget#workspace {{
        background: {t.base};
        border-top-left-radius: 24px;
        border-bottom-left-radius: 24px;
    }}
    QStackedWidget#workspace > QWidget {{ background: transparent; }}
    QWidget#sidebar {{ background: {t.crust}; }}

    QLabel {{ background: transparent; }}
    QLabel#logo {{ border-radius: 12px; font-size: 16px; font-weight: 700; }}
    QLabel#brandTitle {{ font-size: 17px; font-weight: 700; letter-spacing: 0.4px; }}
    QLabel#sidebarFooter {{ color: {t.text_dim}; font-size: 11px; }}
    QLabel#title {{ font-size: 24px; font-weight: 700; }}
    QLabel#subtitle {{ color: {t.text_muted}; font-size: 13px; }}
    QLabel#hint {{ color: {t.text_dim}; font-size: 12px; }}
    QLabel#sectionTitle {{ color: {t.text_dim}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
    QLabel#cardLabel {{ color: {t.text_dim}; font-size: 11px; font-weight: 700; }}
    QLabel#cardValue {{ color: {t.text_main}; font-size: 30px; font-weight: 800; }}
    QLabel#cardDelta {{ color: {t.text_dim}; font-size: 11px; }}
    QLabel#themeCardName {{ font-weight: 600; }}
    QLabel#chip {{ background: {rgba(t.accent, 12)}; color: {t.accent}; border-radius: 9px; padding: 3px 10px; font-weight: 600; font-size: 12px; }}
    QLabel#chipOk {{ background: {rgba(t.success, 14)}; color: {t.success}; border-radius: 9px; padding: 3px 10px; font-weight: 600; font-size: 12px; }}
    QLabel#chipWarn {{ background: {rgba(t.warning, 14)}; color: {t.warning}; border-radius: 9px; padding: 3px 10px; font-weight: 600; font-size: 12px; }}

    QListWidget#nav {{
        background: transparent; border: 0;
        color: {t.text_muted}; font-size: 13px;
        outline: 0;
    }}
    QListWidget#nav::item {{ padding: 9px 12px; margin: 1px 0; border-radius: 10px; color: {t.text_muted}; }}
    QListWidget#nav::item:hover {{ background: {t.surface}; color: {t.text_main}; }}
    QListWidget#nav::item:selected {{ background: {rgba(t.accent, 16)}; color: {t.accent}; font-weight: 600; }}

    QPushButton {{ background: {t.accent}; color: {t.accent_on}; border: 1px solid transparent; border-radius: 10px; padding: 9px 18px; font-weight: 600; }}
    QPushButton:hover {{ background: {t.accent_hover}; }}
    QPushButton:pressed {{ background: {t.accent}; }}
    QPushButton:focus {{ border: 1px solid {t.accent_on}; }}
    QPushButton:disabled {{ background: {t.surface_high}; color: {t.text_dim}; }}
    QPushButton#secondary {{ background: {t.surface_high}; color: {t.text_main}; border: 1px solid {t.border}; }}
    QPushButton#secondary:hover {{ background: {t.surface_highest}; }}
    QPushButton#secondary:disabled {{ background: {t.surface}; color: {t.text_dim}; border-color: {t.border_subtle}; }}
    QPushButton#danger {{ background: {t.error}; color: {t.on_error}; }}
    QPushButton#danger:hover {{ background: {t.error}; }}
    QPushButton#danger:disabled {{ background: {t.surface_high}; color: {t.text_dim}; border-color: {t.border_subtle}; }}
    QPushButton#themeCard {{ background: {t.surface}; color: {t.text_main}; border: 1px solid {t.border_subtle}; border-radius: {t.radius_md}px; padding: 12px; text-align: left; }}
    QPushButton#themeCard:hover {{ background: {t.surface_high}; }}
    QPushButton#themeCard[selected="true"] {{ border: 2px solid {t.accent}; background: {rgba(t.accent, 10)}; }}

    QFrame#card {{ background: {t.surface}; border: 1px solid {t.border_subtle}; border-radius: {t.radius_md}px; }}

    QGroupBox {{
        background: {t.surface}; border: 1px solid {t.border_subtle};
        border-radius: {t.radius_md}px; margin-top: 14px; padding: 16px 14px 12px 14px; font-weight: 600;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; top: 2px; padding: 0 6px; color: {t.text_muted}; font-size: 12px; }}

    QLineEdit, QComboBox, QSpinBox {{
        background: {t.mantle}; color: {t.text_main}; border: 1px solid {t.border_subtle};
        border-radius: 10px; padding: 8px 12px;
        selection-background-color: {t.accent}; selection-color: {t.accent_on};
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border: 1px solid {t.border}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {t.accent}; }}
    QLineEdit:disabled {{ color: {t.text_dim}; }}
    QComboBox::drop-down {{ border: 0; width: 26px; }}
    QComboBox::down-arrow {{ width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 8px solid {t.text_dim}; margin-right: 12px; }}
    QComboBox QAbstractItemView {{ background: {t.surface}; color: {t.text_main}; border: 1px solid {t.border}; border-radius: 10px; padding: 4px; selection-background-color: {rgba(t.accent, 18)}; selection-color: {t.accent}; outline: 0; }}
    QSpinBox::up-button, QSpinBox::down-button {{ background: transparent; border: 0; width: 18px; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ border-radius: 4px; background: {rgba(t.accent, 16)}; }}
    QSpinBox::up-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid {t.text_dim}; }}
    QSpinBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {t.text_dim}; }}
    QCheckBox {{ spacing: 8px; background: transparent; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px; border: 1px solid {t.border}; background: {t.mantle}; }}
    QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
    QCheckBox::indicator:checked {{ background: {t.accent}; border-color: {t.accent}; }}

    QTabWidget::pane {{ border: 0; background: transparent; }}
    QTabWidget > QWidget {{ background: transparent; }}
    QTabBar {{ background: transparent; }}
    QTabBar::tab {{
        background: transparent; color: {t.text_muted};
        padding: 8px 16px; margin: 0 4px 8px 0; border-radius: 9px;
    }}
    QTabBar::tab:hover {{ background: {t.surface}; color: {t.text_main}; }}
    QTabBar::tab:selected {{ background: {rgba(t.accent, 16)}; color: {t.accent}; font-weight: 600; }}

    QTableWidget {{
        background: {t.surface}; color: {t.text_main}; border: 1px solid {t.border_subtle};
        border-radius: 12px; gridline-color: {t.border_subtle};
        selection-background-color: {rgba(t.accent, 22)}; selection-color: {t.text_main};
    }}
    QTableWidget::item {{ padding: 6px 10px; border: 0; }}
    QTableWidget::item:selected {{ background: {rgba(t.accent, 22)}; }}
    QHeaderView::section {{         background: {t.surface}; color: {t.text_dim}; border: 0; border-bottom: 1px solid {t.border_subtle}; padding: 10px 10px; font-weight: 600; text-align: left; }}
    QTableCornerButton::section {{ background: {t.surface}; border: 0; }}

    QProgressBar {{ background: {t.mantle}; border: 0; border-radius: 7px; min-width: 120px; min-height: 14px; text-align: center; color: {t.text_main}; }}
    QProgressBar::chunk {{ background: {t.accent}; border-radius: 7px; }}

    QTextEdit {{
        background: {t.mantle}; color: {t.text_main}; border: 1px solid {t.border_subtle};
        border-radius: {t.radius_md}px; padding: 10px;
        selection-background-color: {t.accent}; selection-color: {t.accent_on};
    }}
    QTextEdit#terminal {{
        background: {t.crust}; color: {t.text_main}; border: 1px solid {t.border_subtle};
        border-radius: {t.radius_md}px; padding: 12px;
        font-family: {t.mono_family}; font-size: 12px;
    }}

    QScrollArea {{ background: transparent; border: 0; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QAbstractScrollArea::corner {{ background: transparent; border: 0; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t.surface_high}; border-radius: 4px; min-height: 32px; }}
    QScrollBar::handle:vertical:hover {{ background: {t.surface_highest}; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {t.surface_high}; border-radius: 4px; min-width: 32px; }}
    QScrollBar::handle:horizontal:hover {{ background: {t.surface_highest}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QMenu {{ background: {t.surface}; color: {t.text_main}; border: 1px solid {t.border}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 8px 24px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {t.surface_high}; }}
    QMenu::item:disabled {{ color: {t.text_dim}; }}
    QMenu::separator {{ height: 1px; background: {t.border_subtle}; margin: 6px 8px; }}
    QToolTip {{ background: {t.surface_highest}; color: {t.text_main}; border: 1px solid {t.border}; border-radius: 6px; padding: 6px 8px; }}
    QStatusBar {{ background: transparent; color: {t.text_dim}; border-top: 1px solid {t.border_subtle}; }}
    QStatusBar::item {{ border: 0; }}
    """
