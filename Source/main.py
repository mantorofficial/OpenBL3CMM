"""
OpenBLCMM for Borderlands 3
A visual hotfix mod editor with category tree, enable/disable toggles,
and OHL-compatible export.

Requirements:
    pip install PySide6
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QModelIndex, Signal, QSettings, QUrl
from PySide6.QtGui import (
    QAction, QColor, QFont, QIcon, QBrush, QPalette, QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QHBoxLayout, QWidget, QMenuBar, QMenu, QToolBar, QStatusBar, QSplitter,
    QTextEdit, QLabel, QLineEdit, QFileDialog, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QPushButton, QGroupBox,
    QCheckBox, QInputDialog, QHeaderView, QAbstractItemView, QFrame,
    QScrollArea, QStyle,
)

from models import ModFile, Category, HotfixEntry
from parser import parse_file, parse_text
from exporter import export_to_file, export_to_text
from commands import simple_to_spark, spark_to_simple, SIMPLE_COMMANDS, COMMAND_HELP


# ──────────────────────────────────────────────
# Constants / styling
# ──────────────────────────────────────────────

APP_NAME = "OpenBL3CMM"
APP_VERSION = "Beta-1.0"
GITHUB_REPO = "mantorofficial/OpenBL3CMM"

# Settings keys
SETTINGS_ORG = "OpenBL3CMM"
SETTINGS_APP = "BL3"


def get_appdata_dir() -> Path:
    """Get the AppData folder for OpenBL3CMM. Creates it if needed."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "Programs" / "OpenBL3CMM"
    else:
        base = Path.home() / ".openbl3cmm"
    base.mkdir(parents=True, exist_ok=True)
    (base / "backups").mkdir(exist_ok=True)
    (base / "datapacks").mkdir(exist_ok=True)
    (base / "mods").mkdir(exist_ok=True)
    return base

# ── Theme system ──
# Each theme is a dict of color tokens. Users can pick one or define their own.

THEMES = {
    "Midnight": {
        "bg":         "#0d0d0d",
        "bg_alt":     "#161616",
        "bg_card":    "#1a1a1a",
        "fg":         "#e0e0e0",
        "fg_dim":     "#808080",
        "accent":     "#f5a623",
        "accent_dim": "#8a6020",
        "enabled":    "#6ecf6e",
        "disabled":   "#e85d75",
        "category":   "#6eaaff",
        "selection":  "#2a2a2a",
        "border":     "#2a2a2a",
        "hover":      "#222222",
        "radius":     "10px",
        "radius_sm":  "8px",
        "font":       '"Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif',
        "font_mono":  '"Cascadia Code", "Fira Code", "Consolas", monospace',
    },
    "Obsidian": {
        "bg":         "#111117",
        "bg_alt":     "#18181f",
        "bg_card":    "#1e1e26",
        "fg":         "#d4d4dc",
        "fg_dim":     "#6e6e82",
        "accent":     "#7c6ef5",
        "accent_dim": "#4e3fb0",
        "enabled":    "#6ecf6e",
        "disabled":   "#e85d75",
        "category":   "#7cb3ff",
        "selection":  "#28283a",
        "border":     "#28283a",
        "hover":      "#222230",
        "radius":     "10px",
        "radius_sm":  "8px",
        "font":       '"Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif',
        "font_mono":  '"Cascadia Code", "Fira Code", "Consolas", monospace',
    },
    "BL3 Orange": {
        "bg":         "#0f0f0f",
        "bg_alt":     "#1a1a1a",
        "bg_card":    "#1f1f1f",
        "fg":         "#e8e8e8",
        "fg_dim":     "#777777",
        "accent":     "#ff9800",
        "accent_dim": "#b36a00",
        "enabled":    "#66bb6a",
        "disabled":   "#ef5350",
        "category":   "#ff9800",
        "selection":  "#2c2c2c",
        "border":     "#2c2c2c",
        "hover":      "#252525",
        "radius":     "10px",
        "radius_sm":  "8px",
        "font":       '"Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif',
        "font_mono":  '"Cascadia Code", "Fira Code", "Consolas", monospace',
    },
    "Soft Dark": {
        "bg":         "#1c1c1e",
        "bg_alt":     "#242426",
        "bg_card":    "#2c2c2e",
        "fg":         "#f0f0f0",
        "fg_dim":     "#8e8e93",
        "accent":     "#0a84ff",
        "accent_dim": "#0060c0",
        "enabled":    "#30d158",
        "disabled":   "#ff453a",
        "category":   "#64d2ff",
        "selection":  "#38383a",
        "border":     "#38383a",
        "hover":      "#303032",
        "radius":     "12px",
        "radius_sm":  "10px",
        "font":       '"SF Pro Display", "Segoe UI", "Helvetica Neue", sans-serif',
        "font_mono":  '"SF Mono", "Cascadia Code", "Consolas", monospace',
    },
    "Soft Purple": {
        "bg":         "#1e1e2e",      # Base
        "bg_alt":     "#181825",      # Mantle
        "bg_card":    "#313244",      # Surface0
        "fg":         "#cdd6f4",      # Text
        "fg_dim":     "#a6adc8",      # Subtext0
        "accent":     "#cba6f7",      # Mauve
        "accent_dim": "#9876c2",
        "enabled":    "#a6e3a1",      # Green
        "disabled":   "#f38ba8",      # Red
        "category":   "#89b4fa",      # Blue
        "selection":  "#45475a",      # Surface1
        "border":     "#45475a",      # Surface1
        "hover":      "#313244",      # Surface0
        "radius":     "10px",
        "radius_sm":  "8px",
        "font":       '"Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif',
        "font_mono":  '"Cascadia Code", "Fira Code", "Consolas", monospace',
    },
    "Catppuccin Mocha": {
        "bg":         "#2b1d1a",      # Deep chocolate
        "bg_alt":     "#332421",      # Dark brown
        "bg_card":    "#3d2d29",      # Warm chocolate card
        "fg":         "#e8ddd4",      # Warm cream text
        "fg_dim":     "#9c867a",      # Muted brown
        "accent":     "#48b9c7",      # Teal/cyan
        "accent_dim": "#2d8a96",      # Darker teal
        "enabled":    "#6ecf6e",      # Green
        "disabled":   "#e85d50",      # Orange-red
        "category":   "#48b9c7",      # Teal for categories
        "selection":  "#60403c",      # The brown you picked
        "border":     "#4d3330",      # Slightly darker border
        "hover":      "#503835",      # Hover between card and selection
        "radius":     "8px",
        "radius_sm":  "6px",
        "font":       '"Ubuntu", "Segoe UI", "Noto Sans", sans-serif',
        "font_mono":  '"Ubuntu Mono", "Cascadia Code", "Consolas", monospace',
    },
}

DEFAULT_THEME = "Midnight"


def get_current_theme_name() -> str:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return s.value("theme", DEFAULT_THEME)


def set_current_theme_name(name: str):
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue("theme", name)


def get_theme() -> dict:
    name = get_current_theme_name()
    return THEMES.get(name, THEMES[DEFAULT_THEME])


import tempfile
import os

_arrow_dir = None

def _ensure_ui_svgs(arrow_color: str, accent_color: str) -> dict:
    """Create temp SVG files for tree arrows and checkboxes. Returns dict of paths."""
    global _arrow_dir
    if _arrow_dir is None:
        _arrow_dir = tempfile.mkdtemp(prefix="openblcmm_ui_")

    def _write(name: str, svg: str) -> str:
        p = os.path.join(_arrow_dir, name)
        with open(p, "w") as f:
            f.write(svg)
        return p.replace("\\", "/")

    paths = {}

    # Arrow: right-pointing triangle (closed)
    paths["arrow_closed"] = _write("arrow_closed.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">'
        f'<polygon points="3,1 11,6 3,11" fill="{arrow_color}"/></svg>'
    )

    # Arrow: down-pointing triangle (open)
    paths["arrow_open"] = _write("arrow_open.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">'
        f'<polygon points="1,3 11,3 6,11" fill="{arrow_color}"/></svg>'
    )

    # Checkbox: checkmark (for checked state)
    paths["check"] = _write("check.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">'
        f'<polyline points="2,6 5,9 10,3" stroke="white" stroke-width="2" fill="none"/></svg>'
    )

    # Checkbox: dash (for indeterminate/partial state)
    paths["dash"] = _write("dash.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">'
        f'<line x1="2" y1="6" x2="10" y2="6" stroke="white" stroke-width="2"/></svg>'
    )

    return paths


def build_stylesheet(t: dict) -> str:
    """Build the full application stylesheet from a theme dict."""
    svgs = _ensure_ui_svgs(t['fg_dim'], t['accent'])
    arrow_closed = svgs["arrow_closed"]
    arrow_open = svgs["arrow_open"]
    check_svg = svgs["check"]
    dash_svg = svgs["dash"]

    # Apply saved font preferences
    font_size = get_font_size()
    custom_font = get_custom_font()
    custom_mono = get_custom_mono_font()

    # Override theme fonts if user has custom ones set
    ui_font = f'"{custom_font}", {t["font"]}' if custom_font else t['font']
    mono_font = f'"{custom_mono}", {t["font_mono"]}' if custom_mono else t['font_mono']

    # Scale derived sizes
    size_sm = max(font_size - 1, 6)
    size_toolbar = max(font_size - 0.5, 6)

    return f"""
/* ── Global ── */
QMainWindow, QWidget {{
    background-color: {t['bg']};
    color: {t['fg']};
    font-family: {ui_font};
    font-size: {font_size}pt;
}}

/* ── Menu bar ── */
QMenuBar {{
    background-color: {t['bg_alt']};
    color: {t['fg']};
    border-bottom: none;
    padding: 2px 0px;
}}
QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 6px;
    margin: 1px 2px;
}}
QMenuBar::item:selected {{
    background-color: {t['selection']};
}}
QMenu {{
    background-color: {t['bg_card']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    border-radius: {t['radius_sm']};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 6px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background-color: {t['selection']};
}}
QMenu::separator {{
    height: 1px;
    background-color: {t['border']};
    margin: 4px 8px;
}}

/* ── Toolbar ── */
QToolBar {{
    background-color: {t['bg_alt']};
    border: none;
    spacing: 3px;
    padding: 4px 6px;
}}
QToolBar QToolButton {{
    color: {t['fg']};
    padding: 5px 10px;
    border-radius: 7px;
    border: none;
    font-size: {size_toolbar}pt;
}}
QToolBar QToolButton:hover {{
    background-color: {t['hover']};
}}
QToolBar QToolButton:pressed {{
    background-color: {t['selection']};
}}

/* ── Tree widget ── */
QTreeWidget {{
    background-color: {t['bg']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    border-radius: {t['radius']};
    outline: none;
    font-size: {font_size}pt;
    padding: 4px;
}}
QTreeWidget::item {{
    padding: 4px 4px;
    border-radius: 6px;
    margin: 1px 2px;
}}
QTreeWidget::item:selected {{
    background-color: {t['selection']};
}}
QTreeWidget::item:hover {{
    background-color: {t['hover']};
}}
QTreeWidget::branch {{
    background-color: transparent;
}}
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    border-image: none;
    image: url("{arrow_closed}");
    padding: 4px;
}}
QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {{
    border-image: none;
    image: url("{arrow_open}");
    padding: 4px;
}}
QHeaderView::section {{
    background-color: {t['bg_alt']};
    color: {t['fg_dim']};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {t['border']};
    font-weight: 600;
    font-size: {size_sm}pt;
    text-transform: uppercase;
}}

/* ── Text inputs ── */
QTextEdit, QLineEdit {{
    background-color: {t['bg_card']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    border-radius: {t['radius_sm']};
    padding: 6px 8px;
    font-family: {mono_font};
    font-size: {font_size}pt;
    selection-background-color: {t['accent_dim']};
}}
QTextEdit:focus, QLineEdit:focus {{
    border-color: {t['accent']};
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {t['bg_alt']};
    color: {t['fg_dim']};
    border-top: none;
    padding: 4px 8px;
    font-size: {size_sm}pt;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {t['bg_card']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    padding: 7px 16px;
    border-radius: {t['radius_sm']};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {t['hover']};
    border-color: {t['accent']};
}}
QPushButton:pressed {{
    background-color: {t['accent_dim']};
}}
QPushButton:disabled {{
    color: {t['fg_dim']};
    background-color: {t['bg_alt']};
    border-color: {t['bg_alt']};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {t['border']};
    border-radius: 2px;
    margin: 2px;
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}

/* ── Group box ── */
QGroupBox {{
    color: {t['accent']};
    border: 1px solid {t['border']};
    border-radius: {t['radius']};
    margin-top: 12px;
    padding: 16px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    font-size: {size_toolbar}pt;
}}

/* ── Combo box ── */
QComboBox {{
    background-color: {t['bg_card']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    padding: 5px 10px;
    border-radius: {t['radius_sm']};
}}
QComboBox:hover {{
    border-color: {t['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {t['bg_card']};
    color: {t['fg']};
    selection-background-color: {t['selection']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 2px;
}}

/* ── Checkbox ── */
QCheckBox {{
    color: {t['fg']};
    spacing: 8px;
}}

/* ── Tree checkboxes ── */
QTreeWidget::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid {t['fg_dim']};
    background-color: transparent;
    margin-right: 4px;
}}
QTreeWidget::indicator:checked {{
    border-color: {t['accent']};
    background-color: {t['accent']};
    image: url("{check_svg}");
}}
QTreeWidget::indicator:unchecked {{
    border-color: {t['fg_dim']};
    background-color: transparent;
}}
QTreeWidget::indicator:indeterminate {{
    border-color: {t['accent']};
    background-color: {t['accent']};
    image: url("{dash_svg}");
}}

/* ── Labels ── */
QLabel {{
    color: {t['fg']};
}}

/* ── Dialogs ── */
QDialog {{
    background-color: {t['bg']};
    color: {t['fg']};
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {t['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {t['fg_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {t['border']};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {t['fg_dim']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── File dialog embedded ── */
QFileDialog {{
    background-color: {t['bg']};
}}

/* ── Drag & drop indicator ── */
QTreeWidget {{
    show-decoration-selected: 1;
}}
QTreeWidget::item:selected:active {{
    background-color: {t['selection']};
}}
"""


# Expose theme colors globally for use in code (updated when theme changes)
_t = get_theme()
COLOR_BG = _t["bg"]
COLOR_BG_ALT = _t["bg_alt"]
COLOR_BG_CARD = _t["bg_card"]
COLOR_FG = _t["fg"]
COLOR_FG_DIM = _t["fg_dim"]
COLOR_ACCENT = _t["accent"]
COLOR_ACCENT_DIM = _t["accent_dim"]
COLOR_ENABLED = _t["enabled"]
COLOR_DISABLED = _t["disabled"]
COLOR_CATEGORY = _t["category"]
COLOR_SELECTION = _t["selection"]
COLOR_BORDER = _t["border"]
COLOR_HOVER = _t["hover"]

# Command-type entry colors — each command type gets its own color
COMMAND_TYPE_COLORS = {
    "set":       "#7cb3ff",  # Blue
    "set_dt":    "#7cb3ff",  # Blue (same as set)
    "edit":      "#a6e3a1",  # Green
    "edit_dt":   "#a6e3a1",  # Green (same as edit)
    "early_set": "#89dceb",  # Cyan
    "merge":     "#cba6f7",  # Purple
    "news":      "#fab387",  # Orange
    "clone":     "#f8a715",  # Yellow/gold (unique)
    "delete":    "#f38ba8",  # Pink
    "create":    "#94e2d5",  # Teal
    "set_cmp":   "#7cb3ff",  # Blue (set family)
    "set_array": "#7cb3ff",  # Blue (set family)
    "set_struct":"#7cb3ff",  # Blue (set family)
    "set_if":    "#7cb3ff",  # Blue (set family)
    "add":       "#a6e3a1",  # Green
    "remove":    "#f38ba8",  # Pink
    "exec":      "#eba0ac",  # Maroon-pink
    "rename":    "#fab387",  # Orange
    "set_mesh":  "#f9e2af",  # Soft yellow
}


# ──────────────────────────────────────────────
# Custom tree item roles
# ──────────────────────────────────────────────

ROLE_DATA = Qt.ItemDataRole.UserRole + 1  # stores Category or HotfixEntry


# ──────────────────────────────────────────────
# Settings helpers
# ──────────────────────────────────────────────

# Default shortcut directory definitions: list of {"label": ..., "path": ...}
# Auto-detect Downloads folder
def _detect_downloads_dir() -> str:
    """Try to find the user's Downloads folder."""
    # Windows
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return str(downloads)
    # XDG (Linux)
    xdg = Path.home() / "downloads"
    if xdg.is_dir():
        return str(xdg)
    return ""

DEFAULT_SHORTCUTS = [
    {"label": "Downloads", "path": _detect_downloads_dir()},
    {"label": "OHL Mods Dir", "path": ""},
    {"label": "Game Install Dir", "path": ""},
    {"label": "Backup Dir", "path": ""},
    {"label": "Last Opened Dir", "path": ""},
]


def load_shortcuts() -> list[dict]:
    """Load shortcut directories from QSettings, merging in any new defaults."""
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    raw = s.value("shortcut_dirs", None)
    shortcuts = None
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, list):
                shortcuts = loaded
        except (json.JSONDecodeError, TypeError):
            pass

    if shortcuts is None:
        return [dict(d) for d in DEFAULT_SHORTCUTS]

    # Merge: if a default label doesn't exist in saved shortcuts, add it
    existing_labels = {sc["label"] for sc in shortcuts}
    for default in DEFAULT_SHORTCUTS:
        if default["label"] not in existing_labels:
            shortcuts.insert(0, dict(default))

    return shortcuts


def save_shortcuts(shortcuts: list[dict]):
    """Save shortcut directories to QSettings."""
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue("shortcut_dirs", json.dumps(shortcuts))


def update_last_opened_dir(directory: str):
    """Update the 'Last Opened Dir' shortcut with the given path."""
    shortcuts = load_shortcuts()
    for sc in shortcuts:
        if sc["label"] == "Last Opened Dir":
            sc["path"] = directory
            break
    save_shortcuts(shortcuts)


# ──────────────────────────────────────────────
# Directory Shortcuts Settings Dialog
# ──────────────────────────────────────────────

class ShortcutDirsDialog(QDialog):
    """Dialog to configure shortcut directories (like BLCMM's sidebar buttons)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Directory Shortcuts")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self.shortcuts = load_shortcuts()

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Set up quick-access directories that appear as buttons in the file dialog.\n"
            "Click 'Browse' to pick a folder, or type the path directly."
        ))

        self.rows: list[tuple[QLineEdit, QLineEdit]] = []

        for sc in self.shortcuts:
            row_layout = QHBoxLayout()

            label_edit = QLineEdit(sc["label"])
            label_edit.setMaximumWidth(160)
            label_edit.setPlaceholderText("Button label")
            row_layout.addWidget(label_edit)

            path_edit = QLineEdit(sc["path"])
            path_edit.setPlaceholderText("Directory path")
            row_layout.addWidget(path_edit)

            browse_btn = QPushButton("Browse")
            browse_btn.setMaximumWidth(70)
            browse_btn.clicked.connect(lambda checked, pe=path_edit: self._browse(pe))
            row_layout.addWidget(browse_btn)

            self.rows.append((label_edit, path_edit))
            layout.addLayout(row_layout)

        # Add / Remove buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Shortcut")
        add_btn.clicked.connect(self._add_row)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self, path_edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Select Directory", path_edit.text())
        if d:
            path_edit.setText(d)

    def _add_row(self):
        row_layout = QHBoxLayout()

        label_edit = QLineEdit("")
        label_edit.setMaximumWidth(160)
        label_edit.setPlaceholderText("Button label")
        row_layout.addWidget(label_edit)

        path_edit = QLineEdit("")
        path_edit.setPlaceholderText("Directory path")
        row_layout.addWidget(path_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(70)
        browse_btn.clicked.connect(lambda checked, pe=path_edit: self._browse(pe))
        row_layout.addWidget(browse_btn)

        self.rows.append((label_edit, path_edit))
        # Insert before the stretch and button box
        main_layout = self.layout()
        main_layout.insertLayout(main_layout.count() - 3, row_layout)

    def get_shortcuts(self) -> list[dict]:
        result = []
        for label_edit, path_edit in self.rows:
            label = label_edit.text().strip()
            path = path_edit.text().strip()
            if label:  # keep entries that have at least a label
                result.append({"label": label, "path": path})
        return result


# ──────────────────────────────────────────────
# Custom File Dialog with shortcut buttons
# ──────────────────────────────────────────────

class ModFileDialog(QDialog):
    """
    A file dialog wrapper that adds shortcut directory buttons on the right side,
    mimicking OpenBLCMM's sidebar (OHL Mods Dir, Game Dir, Backup Dir, etc.).
    """

    def __init__(self, parent=None, mode="open", caption="Open BL3 Hotfix Mod",
                 default_name="", filter_str="BL3 Hotfix Mods (*.bl3hotfix);;BLMOD Files (*.blmod);;Text Files (*.txt);;All Files (*)"):
        super().__init__(parent)
        self.setWindowTitle(caption)
        self.setMinimumWidth(900)
        self.setMinimumHeight(550)
        self.selected_path = ""

        layout = QHBoxLayout(self)

        # Left: the actual QFileDialog widget (embedded)
        self.file_dialog = QFileDialog(self)
        self.file_dialog.setWindowFlags(Qt.WindowType.Widget)  # embed as widget, not separate window
        self.file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.file_dialog.setNameFilter(filter_str)

        if mode == "save":
            self.file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            if default_name:
                self.file_dialog.selectFile(default_name)
        else:
            self.file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
            self.file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        # Set initial directory from Last Opened Dir if available
        shortcuts = load_shortcuts()
        for sc in shortcuts:
            if sc["label"] == "Last Opened Dir" and sc["path"] and Path(sc["path"]).is_dir():
                self.file_dialog.setDirectory(sc["path"])
                break

        self.file_dialog.accepted.connect(self._on_accepted)
        self.file_dialog.rejected.connect(self.reject)

        layout.addWidget(self.file_dialog, stretch=3)

        # Right: shortcut buttons panel
        btn_panel = QVBoxLayout()
        btn_panel.setSpacing(6)

        btn_panel.addWidget(QLabel("Quick Access"))
        btn_panel.addWidget(self._make_separator())

        for sc in shortcuts:
            if not sc["label"]:
                continue
            btn = QPushButton(sc["label"])
            btn.setMinimumHeight(32)
            btn.setEnabled(bool(sc["path"] and Path(sc["path"]).is_dir()))
            if sc["path"]:
                btn.setToolTip(sc["path"])
                btn.clicked.connect(lambda checked, p=sc["path"]: self._jump_to(p))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BG_ALT};
                    color: {COLOR_FG};
                    border: 1px solid {COLOR_BORDER};
                    padding: 6px 12px;
                    border-radius: 3px;
                    text-align: left;
                    font-size: 9pt;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SELECTION};
                    border-color: {COLOR_ACCENT};
                }}
                QPushButton:disabled {{
                    color: #585b70;
                    border-color: #313244;
                }}
            """)
            btn_panel.addWidget(btn)

        btn_panel.addStretch()

        # Settings button at bottom
        settings_btn = QPushButton("Configure Shortcuts...")
        settings_btn.setMinimumHeight(28)
        settings_btn.clicked.connect(self._open_settings)
        btn_panel.addWidget(settings_btn)

        layout.addLayout(btn_panel, stretch=0)

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {COLOR_BORDER};")
        return sep

    def _jump_to(self, path: str):
        if Path(path).is_dir():
            self.file_dialog.setDirectory(path)

    def _on_accepted(self):
        files = self.file_dialog.selectedFiles()
        if files:
            self.selected_path = files[0]
            # Update last opened dir
            parent_dir = str(Path(files[0]).parent)
            update_last_opened_dir(parent_dir)
        self.accept()

    def _open_settings(self):
        dlg = ShortcutDirsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_shortcuts(dlg.get_shortcuts())
            QMessageBox.information(
                self, "Shortcuts Updated",
                "Directory shortcuts have been updated.\n"
                "They'll take effect next time you open a file dialog."
            )

    def get_path(self) -> str:
        return self.selected_path


# ──────────────────────────────────────────────
# New Hotfix Entry Dialog
# ──────────────────────────────────────────────

def auto_format_hotfix(text: str) -> str:
    """
    Auto-format a hotfix command with BLCMM-style indentation.
    Formats struct values like (Key=Value, ...) into multi-line indented form.
    Works for both simple commands and raw Spark format.
    """
    lines = text.strip().splitlines()
    single = " ".join(l.strip() for l in lines)

    # For simple commands: "set OBJ ATTR VALUE"
    # Split into header (cmd obj attr) and value
    header = ""
    value_part = ""

    # Detect simple command
    simple_cmds = ("set ", "edit ", "merge ", "early_set ", "set_cmp ")
    if any(single.lower().startswith(c) for c in simple_cmds):
        parts = single.split(None, 3)
        if len(parts) >= 4:
            header = f"{parts[0]} {parts[1]} {parts[2]}"
            value_part = parts[3]
        elif len(parts) == 3:
            return single  # No value to format
        else:
            return single
    elif single.startswith("Spark") or single.startswith("Inject"):
        # Raw Spark format — find the value after the last ,0,,  or ,,
        # Look for the value portion (after from_length,,)
        idx = single.rfind(",0,,")
        if idx >= 0:
            header = single[:idx + 4]  # include ,0,,
            value_part = single[idx + 4:]
        else:
            idx = single.rfind(",,")
            if idx >= 0:
                header = single[:idx + 2]
                value_part = single[idx + 2:]
            else:
                return single
    else:
        # Unknown format — try generic struct formatting
        value_part = single
        header = ""

    # If value has no parens, no formatting needed
    if '(' not in value_part:
        return single

    # Format the value part with indentation
    formatted_value = _format_struct(value_part, base_indent=1 if header else 0)

    if header:
        return f"{header}\n{formatted_value}"
    return formatted_value


def _format_struct(text: str, base_indent: int = 0) -> str:
    """Format a BL3 struct value with BLCMM-style indentation."""
    result = []
    indent = base_indent
    i = 0
    text = text.strip()

    while i < len(text):
        ch = text[i]

        if ch == '(':
            result.append('(\n')
            indent += 1
            result.append('    ' * indent)
            i += 1
            while i < len(text) and text[i] == ' ':
                i += 1
            continue
        elif ch == ')':
            # Remove trailing whitespace/comma
            content = ''.join(result).rstrip()
            if content.endswith(','):
                content = content[:-1]
            result = [content]
            result.append('\n')
            indent = max(0, indent - 1)
            result.append('    ' * indent)
            result.append(')')
            i += 1
            continue
        elif ch == ',' and indent > base_indent:
            result.append(',\n')
            result.append('    ' * indent)
            i += 1
            while i < len(text) and text[i] == ' ':
                i += 1
            continue
        else:
            result.append(ch)
            i += 1

    return ''.join(result)


class NewEntryDialog(QDialog):
    """Dialog for creating a new hotfix entry — three modes: Simple, Raw Text, or Spark."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Hotfix Entry")
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(6)

        # Mode selector
        mode_layout = QHBoxLayout()
        self.mode_simple = QPushButton("Simple Command")
        self.mode_raw_text = QPushButton("Raw Text")
        self.mode_raw_spark = QPushButton("Spark Format")
        for btn in (self.mode_simple, self.mode_raw_text, self.mode_raw_spark):
            btn.setCheckable(True)
        self.mode_raw_text.setChecked(True)
        self.mode_simple.clicked.connect(lambda: self._set_mode("simple"))
        self.mode_raw_text.clicked.connect(lambda: self._set_mode("text"))
        self.mode_raw_spark.clicked.connect(lambda: self._set_mode("spark"))
        mode_layout.addWidget(self.mode_raw_text)
        mode_layout.addWidget(self.mode_simple)
        mode_layout.addWidget(self.mode_raw_spark)
        self._main_layout.addLayout(mode_layout)

        # ── Simple command mode ──
        self.simple_widget = QWidget()
        sl = QFormLayout(self.simple_widget)
        sl.setContentsMargins(0, 4, 0, 0)

        self.cmd_combo = QComboBox()
        self.cmd_combo.addItems(SIMPLE_COMMANDS)
        self.cmd_combo.currentTextChanged.connect(self._update_help)
        sl.addRow("Command:", self.cmd_combo)

        self.simple_edit = QLineEdit()
        self.simple_edit.setPlaceholderText("/Game/Path/Object PropertyName Value")
        sl.addRow("Arguments:", self.simple_edit)

        self.help_label = QLabel("")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet(f"color: {COLOR_FG_DIM}; font-style: italic;")
        sl.addRow("", self.help_label)

        self.preview_label = QLabel("(type arguments above)")
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextFormat(Qt.TextFormat.PlainText)
        self.preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.preview_label.setStyleSheet(
            f"color: {COLOR_FG_DIM}; font-family: monospace; "
            f"background-color: {COLOR_BG_CARD}; padding: 8px; border-radius: 4px;"
        )
        sl.addRow("Converts to:", self.preview_label)
        self.simple_edit.textChanged.connect(self._update_preview)

        self._main_layout.addWidget(self.simple_widget)
        self.simple_widget.hide()

        # ── Raw Text mode — big text area like a notepad ──
        self.text_widget = QWidget()
        tl = QVBoxLayout(self.text_widget)
        tl.setContentsMargins(0, 4, 0, 0)
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setPlaceholderText(
            "Type or paste the full hotfix line(s) here...\n\n"
            "e.g. SparkPatchEntry,(1,1,0,),/Game/Path/Object,Property,0,,Value"
        )
        self.raw_text_edit.setMinimumHeight(200)
        tl.addWidget(self.raw_text_edit)

        btn_fmt = QPushButton("Auto Format")
        btn_fmt.clicked.connect(self._auto_format_raw)
        tl.addWidget(btn_fmt)

        # Attach syntax highlighter to raw text mode
        from hotfix_highlighter import HotfixHighlighter
        self._highlighter = HotfixHighlighter(self.raw_text_edit.document())

        # Bracket matching for raw text mode
        self.raw_text_edit.cursorPositionChanged.connect(
            lambda: self._highlight_bracket(self.raw_text_edit)
        )

        self._main_layout.addWidget(self.text_widget)

        # ── Raw Spark mode ──
        self.spark_widget = QWidget()
        rl = QFormLayout(self.spark_widget)
        rl.setContentsMargins(0, 4, 0, 0)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "SparkPatchEntry", "SparkLevelPatchEntry",
            "SparkCharacterLoadedEntry", "SparkEarlyLevelPatchEntry", "InjectNewsItem",
        ])
        rl.addRow("Type:", self.type_combo)

        self.params_edit = QLineEdit("(1,1,0,)")
        self.params_edit.setPlaceholderText("(1,1,0,) or (1,2,0,MatchAll)")
        rl.addRow("Params:", self.params_edit)

        self.object_edit = QLineEdit()
        self.object_edit.setPlaceholderText("/Game/Path/To/Object.Object")
        rl.addRow("Object:", self.object_edit)

        self.attr_edit = QLineEdit()
        self.attr_edit.setPlaceholderText("PropertyName")
        rl.addRow("Attribute:", self.attr_edit)

        self.dtkey_edit = QLineEdit()
        self.dtkey_edit.setPlaceholderText("DataTable key (optional)")
        rl.addRow("DT Key:", self.dtkey_edit)

        self.index_edit = QLineEdit("0")
        rl.addRow("Index:", self.index_edit)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Value")
        rl.addRow("Value:", self.value_edit)

        self._main_layout.addWidget(self.spark_widget)
        self.spark_widget.hide()

        # ── Common: comment + buttons ──
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Description comment (optional)")
        self._main_layout.addWidget(QLabel("Comment:"))
        self._main_layout.addWidget(self.comment_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        self._main_layout.addWidget(buttons)

        self._update_help()

    def _on_ok(self):
        """Validate before accepting."""
        from hotfix_highlighter import validate_hotfix

        # Get the text that would be submitted
        if self.mode_simple.isChecked():
            cmd = self.cmd_combo.currentText()
            args = self.simple_edit.text().strip()
            text = f"{cmd} {args}" if args else ""
        elif self.mode_raw_spark.isChecked():
            htype = self.type_combo.currentText()
            params = self.params_edit.text().strip()
            obj = self.object_edit.text().strip()
            attr = self.attr_edit.text().strip()
            dtkey = self.dtkey_edit.text().strip()
            idx = self.index_edit.text().strip()
            val = self.value_edit.text().strip()
            if htype == "InjectNewsItem":
                text = f"InjectNewsItem,{val}"
            else:
                text = f"{htype},{params},{obj},{attr},{dtkey},{idx},,{val}"
        else:
            text = self.raw_text_edit.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, "Empty", "No command entered.")
            return

        problems = validate_hotfix(text)
        if problems:
            msg = "Your code has the following potential problems:\n\n"
            for p in problems:
                msg += f"  • {p}\n"
            msg += "\nContinue anyway?"
            reply = QMessageBox.question(
                self, "Confirm", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.accept()

    def _auto_format_raw(self):
        """Auto-format the raw text command."""
        text = self.raw_text_edit.toPlainText().strip()
        formatted = auto_format_hotfix(text)
        self.raw_text_edit.setPlainText(formatted)

    def _highlight_bracket(self, editor):
        """Highlight matching bracket in a QTextEdit."""
        from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor

        editor.setExtraSelections([])
        cursor = editor.textCursor()
        text = editor.toPlainText()
        pos = cursor.position()
        if not text:
            return

        ch = text[pos] if pos < len(text) else ''
        ch_before = text[pos - 1] if pos > 0 else ''
        match_pos = bracket_pos = -1

        def find_fwd(t, p):
            d = 0
            for i in range(p, len(t)):
                if t[i] == '(': d += 1
                elif t[i] == ')':
                    d -= 1
                    if d == 0: return i
            return -1

        def find_bwd(t, p):
            d = 0
            for i in range(p, -1, -1):
                if t[i] == ')': d += 1
                elif t[i] == '(':
                    d -= 1
                    if d == 0: return i
            return -1

        if ch == '(':
            bracket_pos, match_pos = pos, find_fwd(text, pos)
        elif ch == ')':
            bracket_pos, match_pos = pos, find_bwd(text, pos)
        elif ch_before == '(':
            bracket_pos, match_pos = pos - 1, find_fwd(text, pos - 1)
        elif ch_before == ')':
            bracket_pos, match_pos = pos - 1, find_bwd(text, pos - 1)

        if match_pos < 0 or bracket_pos < 0:
            return

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#5a5a2a"))
        fmt.setForeground(QColor("#ffff00"))
        selections = []
        for p in (bracket_pos, match_pos):
            sel = editor.ExtraSelection()
            c = QTextCursor(editor.document())
            c.setPosition(p)
            c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            sel.format = fmt
            selections.append(sel)
        editor.setExtraSelections(selections)

    def _set_mode(self, mode: str):
        self.mode_simple.setChecked(mode == "simple")
        self.mode_raw_text.setChecked(mode == "text")
        self.mode_raw_spark.setChecked(mode == "spark")
        self.simple_widget.setVisible(mode == "simple")
        self.text_widget.setVisible(mode == "text")
        self.spark_widget.setVisible(mode == "spark")
        # Let Qt recalculate the natural size
        self.setMinimumSize(0, 0)
        self.resize(self.sizeHint())

    def _update_help(self):
        cmd = self.cmd_combo.currentText()
        self.help_label.setText(COMMAND_HELP.get(cmd, ""))
        self._update_preview()

    def _update_preview(self):
        cmd = self.cmd_combo.currentText()
        args = self.simple_edit.text().strip()
        if args:
            result = simple_to_spark(f"{cmd} {args}")
            self.preview_label.setText(result if result else "(invalid — check syntax)")
        else:
            self.preview_label.setText("(type arguments above)")

    def get_entry(self) -> HotfixEntry | None:
        comment = self.comment_edit.text().strip()
        original_cmd = ""

        if self.mode_simple.isChecked():
            cmd = self.cmd_combo.currentText()
            original_cmd = cmd.lower()
            args = self.simple_edit.text().strip()
            if not args:
                return None
            raw = simple_to_spark(f"{cmd} {args}")
            if not raw:
                return None
        elif self.mode_raw_spark.isChecked():
            htype = self.type_combo.currentText()
            params = self.params_edit.text().strip()
            obj = self.object_edit.text().strip()
            attr = self.attr_edit.text().strip()
            dtkey = self.dtkey_edit.text().strip()
            idx = self.index_edit.text().strip()
            val = self.value_edit.text().strip()
            if htype == "InjectNewsItem":
                raw = f"InjectNewsItem,{val}"
            else:
                raw = f"{htype},{params},{obj},{attr},{dtkey},{idx},,{val}"
        else:
            # Raw text mode
            text = self.raw_text_edit.toPlainText().strip()
            if not text:
                return None
            # Collapse multi-line to single line
            raw = " ".join(line.strip() for line in text.splitlines())
            # Clean up struct spacing
            import re
            raw = re.sub(r'\(\s+', '(', raw)
            raw = re.sub(r'\s+\)', ')', raw)
            raw = re.sub(r',\s+', ',', raw)
            # Detect original command from the text
            first_word = raw.split()[0].lower() if raw.split() else ""
            is_spark = first_word.startswith("spark") or first_word.startswith("inject")
            if not is_spark:
                original_cmd = first_word
                converted = simple_to_spark(raw)
                if converted:
                    raw = converted

        entry = HotfixEntry(raw_line=raw, comment=comment, enabled=True)
        if original_cmd:
            entry._original_cmd = original_cmd
        return entry


# ──────────────────────────────────────────────
# Edit Entry Dialog
# ──────────────────────────────────────────────

class EditEntryDialog(QDialog):
    """Dialog for editing an existing hotfix entry — shows simple command form."""

    def __init__(self, entry: HotfixEntry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Hotfix Entry")
        self.resize(800, 400)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.entry = entry
        self._original_raw_line = entry.raw_line  # preserve for DT column recovery

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Top bar with comment + auto format
        top = QHBoxLayout()
        top.addWidget(QLabel("Comment:"))
        self.comment_edit = QLineEdit(entry.comment)
        top.addWidget(self.comment_edit, stretch=1)
        btn_fmt = QPushButton("Auto Format")
        btn_fmt.clicked.connect(self._auto_format)
        top.addWidget(btn_fmt)
        layout.addLayout(top)

        layout.addWidget(QLabel("Command:"))
        self.raw_edit = QTextEdit()
        display = entry.simple_form if entry.simple_form else entry.raw_line
        # Auto-format structs for readability
        if '(' in display:
            display = auto_format_hotfix(display)
        self.raw_edit.setPlainText(display)
        self.raw_edit.setMinimumHeight(150)
        layout.addWidget(self.raw_edit, stretch=1)

        # Attach syntax highlighter
        from hotfix_highlighter import HotfixHighlighter
        self._highlighter = HotfixHighlighter(self.raw_edit.document())

        # Bracket matching
        self.raw_edit.cursorPositionChanged.connect(self._highlight_matching_bracket)
        self._bracket_selections = []

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.adjustSize()

    def _on_ok(self):
        """Validate before accepting."""
        from hotfix_highlighter import validate_hotfix
        text = self.raw_edit.toPlainText().strip()
        problems = validate_hotfix(text)
        if problems:
            msg = "Your code has the following potential problems:\n\n"
            for p in problems:
                msg += f"  • {p}\n"
            msg += "\nContinue anyway?"
            reply = QMessageBox.question(
                self, "Confirm", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.accept()

    def _auto_format(self):
        """Auto-format the command text with proper indentation."""
        text = self.raw_edit.toPlainText().strip()
        formatted = auto_format_hotfix(text)
        self.raw_edit.setPlainText(formatted)

    def _highlight_matching_bracket(self):
        """Highlight matching bracket when cursor is on ( or )."""
        from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor

        # Clear previous highlights
        self.raw_edit.setExtraSelections([])

        cursor = self.raw_edit.textCursor()
        text = self.raw_edit.toPlainText()
        pos = cursor.position()

        if pos >= len(text):
            return

        ch = text[pos] if pos < len(text) else ''
        # Also check character before cursor
        ch_before = text[pos - 1] if pos > 0 else ''

        match_pos = -1
        bracket_pos = -1

        if ch == '(':
            bracket_pos = pos
            match_pos = self._find_matching_forward(text, pos)
        elif ch == ')':
            bracket_pos = pos
            match_pos = self._find_matching_backward(text, pos)
        elif ch_before == '(':
            bracket_pos = pos - 1
            match_pos = self._find_matching_forward(text, pos - 1)
        elif ch_before == ')':
            bracket_pos = pos - 1
            match_pos = self._find_matching_backward(text, pos - 1)

        if match_pos < 0 or bracket_pos < 0:
            return

        # Create highlight format
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#5a5a2a"))
        fmt.setForeground(QColor("#ffff00"))

        selections = []
        for p in (bracket_pos, match_pos):
            sel = self.raw_edit.ExtraSelection()
            c = QTextCursor(self.raw_edit.document())
            c.setPosition(p)
            c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            sel.format = fmt
            selections.append(sel)

        self.raw_edit.setExtraSelections(selections)

    def _find_matching_forward(self, text, pos):
        """Find matching ) for ( at pos."""
        depth = 0
        for i in range(pos, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _find_matching_backward(self, text, pos):
        """Find matching ( for ) at pos."""
        depth = 0
        for i in range(pos, -1, -1):
            if text[i] == ')':
                depth += 1
            elif text[i] == '(':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def apply(self):
        self.entry.comment = self.comment_edit.text().strip()
        text = self.raw_edit.toPlainText().strip()

        # Collapse multi-line to single line (for auto-formatted structs)
        collapsed = " ".join(line.strip() for line in text.splitlines())
        # Clean up struct spacing: "( Key=Val )" → "(Key=Val)"
        import re
        collapsed = re.sub(r'\(\s+', '(', collapsed)
        collapsed = re.sub(r'\s+\)', ')', collapsed)
        collapsed = re.sub(r',\s+', ',', collapsed)

        # Check if it's already Spark format — don't convert
        spark_types = ("SparkPatchEntry", "SparkLevelPatchEntry",
                       "SparkCharacterLoadedEntry", "SparkEarlyLevelPatchEntry",
                       "InjectNewsItem")
        if any(collapsed.startswith(st) for st in spark_types):
            self.entry.raw_line = collapsed
            self.entry._parse()
            return

        # If original was a Type 2 DataTable hotfix, recover the column name
        # and rebuild the Spark line from the simplified "set TABLE ROW VALUE"
        old_raw = self._original_raw_line
        if old_raw and "(1,2,0" in old_raw:
            old_parts = old_raw.split(",")
            # Type 2 layout: HotfixType,(params),object,row,column,fromlength,fromval,toval
            # Find column: it's after params, object, row
            old_col = old_parts[4] if len(old_parts) > 4 else ""
            if old_col:
                # Parse the simple form: "set TABLE ROW VALUE" or "edit TABLE ROW VALUE"
                cmd_parts = collapsed.split(None, 3)
                if len(cmd_parts) >= 3:
                    cmd_name = cmd_parts[0].lower()
                    table = cmd_parts[1]
                    row = cmd_parts[2]
                    value = cmd_parts[3] if len(cmd_parts) > 3 else ""

                    # Determine hotfix type from command or original
                    if cmd_name == "edit" or old_raw.startswith("SparkLevelPatchEntry"):
                        # Recover params from original
                        params_start = old_raw.index(",(") + 1
                        params_end = old_raw.index("),", params_start) + 1
                        params = old_raw[params_start:params_end]
                        self.entry.raw_line = f"SparkLevelPatchEntry,{params},{table},{row},{old_col},0,,{value}"
                    else:
                        self.entry.raw_line = f"SparkPatchEntry,(1,2,0,),{table},{row},{old_col},0,,{value}"
                    self.entry._parse()
                    return

        converted = simple_to_spark(collapsed)
        if converted:
            self.entry.raw_line = converted
        else:
            self.entry.raw_line = collapsed
        self.entry._parse()


# ──────────────────────────────────────────────
# Mod Metadata Dialog
# ──────────────────────────────────────────────

class MetadataDialog(QDialog):
    """Dialog for editing mod metadata."""

    def __init__(self, mod: ModFile, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mod Properties")
        self.setMinimumWidth(500)
        self.mod = mod

        layout = QFormLayout(self)

        self.name_edit = QLineEdit(mod.name)
        layout.addRow("Name:", self.name_edit)

        self.version_edit = QLineEdit(mod.version)
        layout.addRow("Version:", self.version_edit)

        self.author_edit = QLineEdit(mod.author)
        layout.addRow("Author:", self.author_edit)

        self.contact_edit = QLineEdit(mod.contact)
        layout.addRow("Contact:", self.contact_edit)

        self.cats_edit = QLineEdit(mod.categories_tag)
        layout.addRow("Categories:", self.cats_edit)

        self.license_edit = QLineEdit(mod.license_name)
        layout.addRow("License:", self.license_edit)

        self.license_url_edit = QLineEdit(mod.license_url)
        layout.addRow("License URL:", self.license_url_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(mod.description)
        self.desc_edit.setMaximumHeight(150)
        layout.addRow("Description:", self.desc_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self):
        self.mod.name = self.name_edit.text().strip()
        self.mod.version = self.version_edit.text().strip()
        self.mod.author = self.author_edit.text().strip()
        self.mod.contact = self.contact_edit.text().strip()
        self.mod.categories_tag = self.cats_edit.text().strip()
        self.mod.license_name = self.license_edit.text().strip()
        self.mod.license_url = self.license_url_edit.text().strip()
        self.mod.description = self.desc_edit.toPlainText().strip()


# ──────────────────────────────────────────────
# Font & Size Settings
# ──────────────────────────────────────────────

def get_font_size() -> int:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return int(s.value("font_size", 10))

def set_font_size(size: int):
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue("font_size", max(6, min(24, size)))

def get_custom_font() -> str:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return s.value("custom_font", "")

def set_custom_font(font: str):
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue("custom_font", font)

def get_custom_mono_font() -> str:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return s.value("custom_mono_font", "")

def set_custom_mono_font(font: str):
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue("custom_mono_font", font)


# Default keyboard shortcuts
DEFAULT_KEY_SHORTCUTS = {
    "New File": "Ctrl+N",
    "Open File": "Ctrl+O",
    "Save": "Ctrl+S",
    "Save As": "Ctrl+Shift+S",
    "Add Category": "Ctrl+H",
    "Add Entry": "Insert",
    "Enable Selected": "Ctrl+B",
    "Disable Selected": "Ctrl+D",
    "Copy": "Ctrl+C",
    "Cut": "Ctrl+X",
    "Paste": "Ctrl+V",
    "Rename": "Ctrl+R",
    "Delete": "Delete",
    "Zoom In": "Ctrl+=",
    "Zoom Out": "Ctrl+-",
    "Reset Zoom": "Ctrl+0",
    "Object Explorer": "Ctrl+E",
}

def get_shortcuts() -> dict[str, str]:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    shortcuts = {}
    for name, default in DEFAULT_KEY_SHORTCUTS.items():
        shortcuts[name] = s.value(f"shortcut/{name}", default)
    return shortcuts

def set_shortcut(name: str, key: str):
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue(f"shortcut/{name}", key)


class ShortcutKeyEdit(QLineEdit):
    """A line edit that captures key sequences, mouse buttons, and wheel.
    Click the field to start listening, press Escape to cancel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._listening = False
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_look()

    def _update_look(self):
        if self._listening:
            self.setStyleSheet("border: 2px solid #f8a715; background-color: rgba(248,167,21,0.15);")
            self.setPlaceholderText("Press a key, click, or scroll...")
        else:
            self.setStyleSheet("")
            self.setPlaceholderText("")

    def _start_listening(self):
        self._listening = True
        self._update_look()
        self.grabKeyboard()
        self.grabMouse()

    def _stop_listening(self):
        self._listening = False
        self._update_look()
        self.releaseKeyboard()
        self.releaseMouse()

    def _mod_parts(self, mods):
        from PySide6.QtCore import Qt as QtCore_Qt
        parts = []
        if mods & QtCore_Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & QtCore_Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if mods & QtCore_Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        return parts

    def mousePressEvent(self, event):
        from PySide6.QtCore import Qt as QtCore_Qt
        if not self._listening:
            self._start_listening()
            return

        parts = self._mod_parts(event.modifiers())
        btn = event.button()
        btn_names = {
            QtCore_Qt.MouseButton.LeftButton: "LeftClick",
            QtCore_Qt.MouseButton.RightButton: "RightClick",
            QtCore_Qt.MouseButton.MiddleButton: "MiddleClick",
            QtCore_Qt.MouseButton.BackButton: "Mouse4",
            QtCore_Qt.MouseButton.ForwardButton: "Mouse5",
        }
        btn_name = btn_names.get(btn, f"Mouse{int(btn)}")
        parts.append(btn_name)
        self.setText("+".join(parts))
        self._stop_listening()

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt as QtCore_Qt
        if not self._listening:
            # Allow Enter/Space to start listening
            if event.key() in (QtCore_Qt.Key.Key_Return, QtCore_Qt.Key.Key_Enter, QtCore_Qt.Key.Key_Space):
                self._start_listening()
            return

        key = event.key()

        # Escape cancels listening
        if key == QtCore_Qt.Key.Key_Escape:
            self._stop_listening()
            return

        # Ignore bare modifier keys
        if key in (QtCore_Qt.Key.Key_Control, QtCore_Qt.Key.Key_Shift,
                   QtCore_Qt.Key.Key_Alt, QtCore_Qt.Key.Key_Meta):
            return

        parts = self._mod_parts(event.modifiers())
        key_seq = QKeySequence(key)
        key_text = key_seq.toString()
        if key_text:
            parts.append(key_text)

        self.setText("+".join(parts))
        self._stop_listening()

    def wheelEvent(self, event):
        if not self._listening:
            # Pass to parent so scroll area works
            event.ignore()
            return

        parts = self._mod_parts(event.modifiers())
        delta = event.angleDelta().y()
        if delta > 0:
            parts.append("WheelUp")
        elif delta < 0:
            parts.append("WheelDown")
        else:
            hdelta = event.angleDelta().x()
            if hdelta > 0:
                parts.append("WheelRight")
            else:
                parts.append("WheelLeft")

        self.setText("+".join(parts))
        self._stop_listening()

    def focusOutEvent(self, event):
        if self._listening:
            self._stop_listening()
        super().focusOutEvent(event)


class ShortcutEditorDialog(QDialog):
    """Dialog for editing keyboard shortcuts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(500, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._edits: dict[str, ShortcutKeyEdit] = {}
        shortcuts = get_shortcuts()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        form = QVBoxLayout(scroll_widget)
        form.setSpacing(4)

        for name, key in shortcuts.items():
            row = QHBoxLayout()
            row.setSpacing(8)
            label = QLabel(name)
            label.setMinimumWidth(150)
            edit = ShortcutKeyEdit()
            edit.setText(key)
            edit.setMinimumWidth(140)
            reset_btn = QPushButton()
            reset_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
            reset_btn.setToolTip("Reset to default")
            reset_btn.setFixedWidth(30)
            reset_btn.setFixedHeight(26)
            default_key = DEFAULT_KEY_SHORTCUTS.get(name, "")
            reset_btn.clicked.connect(lambda checked, e=edit, d=default_key: e.setText(d))
            row.addWidget(label)
            row.addWidget(edit, 1)
            row.addWidget(reset_btn)
            form.addLayout(row)
            self._edits[name] = edit

        form.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_reset_all = QPushButton("Reset All to Defaults")
        btn_reset_all.clicked.connect(self._reset_all)
        btn_layout.addWidget(btn_reset_all)
        btn_layout.addStretch()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _reset_all(self):
        for name, edit in self._edits.items():
            edit.setText(DEFAULT_KEY_SHORTCUTS.get(name, ""))

    def get_shortcuts(self) -> dict[str, str]:
        return {name: edit.text() for name, edit in self._edits.items()}


# Default command type colors
DEFAULT_COMMAND_COLORS = {
    "set":       "#7cb3ff",
    "set_dt":    "#7cb3ff",
    "edit":      "#a6e3a1",
    "edit_dt":   "#a6e3a1",
    "early_set": "#89dceb",
    "merge":     "#cba6f7",
    "news":      "#fab387",
    "clone":     "#f8a715",
    "delete":    "#f38ba8",
    "create":    "#94e2d5",
    "set_cmp":   "#b4befe",
    "set_array": "#7cb3ff",
    "set_struct": "#7cb3ff",
    "set_if":    "#7cb3ff",
    "add":       "#a6e3a1",
    "remove":    "#f38ba8",
    "exec":      "#eba0ac",
    "rename":    "#fab387",
    "set_mesh":  "#f9e2af",
}

def get_command_colors() -> dict[str, str]:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    colors = {}
    for cmd, default in DEFAULT_COMMAND_COLORS.items():
        colors[cmd] = s.value(f"cmd_color/{cmd}", default)
    return colors

def set_command_color(cmd: str, color: str):
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue(f"cmd_color/{cmd}", color)


class ColorButton(QPushButton):
    """A button that shows a color and opens a color picker on click."""

    def __init__(self, color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(40, 26)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        self.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #666; border-radius: 3px;"
        )

    def _pick_color(self):
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self._color), self.parentWidget(), "Pick Color")
        if color.isValid():
            self._color = color.name()
            self._update_style()

    def color(self) -> str:
        return self._color


class ColorCodingDialog(QDialog):
    """Dialog for customizing command type colors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Color Coding")
        self.resize(400, 500)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        form = QVBoxLayout(scroll_widget)
        form.setSpacing(4)

        self._buttons: dict[str, ColorButton] = {}
        colors = get_command_colors()

        # Group related commands
        groups = [
            ("Set family", ["set", "set_dt", "set_array", "set_struct", "set_if", "set_cmp"]),
            ("Edit family", ["edit", "edit_dt", "early_set"]),
            ("Modify", ["add", "remove", "merge"]),
            ("Object", ["clone", "delete", "create", "rename"]),
            ("Other", ["news", "exec"]),
        ]

        for group_name, cmds in groups:
            group_label = QLabel(f"— {group_name} —")
            group_label.setStyleSheet("font-weight: bold; padding-top: 6px;")
            form.addWidget(group_label)

            for cmd in cmds:
                if cmd not in colors:
                    continue
                row = QHBoxLayout()
                row.setSpacing(8)
                label = QLabel(cmd)
                label.setMinimumWidth(100)
                btn = ColorButton(colors[cmd])
                reset_btn = QPushButton()
                reset_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
                reset_btn.setToolTip("Reset to default")
                reset_btn.setFixedWidth(30)
                reset_btn.setFixedHeight(26)
                default_color = DEFAULT_COMMAND_COLORS.get(cmd, "#ffffff")
                reset_btn.clicked.connect(
                    lambda checked, b=btn, d=default_color: (
                        setattr(b, '_color', d), b._update_style()
                    )
                )
                row.addWidget(label)
                row.addStretch()
                row.addWidget(btn)
                row.addWidget(reset_btn)
                form.addLayout(row)
                self._buttons[cmd] = btn

        form.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_reset_all = QPushButton("Reset All to Defaults")
        btn_reset_all.clicked.connect(self._reset_all)
        btn_layout.addWidget(btn_reset_all)
        btn_layout.addStretch()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _reset_all(self):
        for cmd, btn in self._buttons.items():
            btn._color = DEFAULT_COMMAND_COLORS.get(cmd, "#ffffff")
            btn._update_style()

    def get_colors(self) -> dict[str, str]:
        return {cmd: btn.color() for cmd, btn in self._buttons.items()}


class FontSettingsDialog(QDialog):
    """Dialog for configuring font family and sizes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Font & Size Settings")
        self.setMinimumWidth(500)

        from PySide6.QtWidgets import QSpinBox, QFontComboBox

        layout = QFormLayout(self)

        # Font size
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 24)
        self.size_spin.setValue(get_font_size())
        self.size_spin.setSuffix(" pt")
        layout.addRow("Font Size:", self.size_spin)

        # UI font
        self.ui_font_combo = QFontComboBox()
        current_ui = get_custom_font()
        if current_ui:
            self.ui_font_combo.setCurrentFont(QFont(current_ui))
        layout.addRow("UI Font:", self.ui_font_combo)

        # Mono font
        self.mono_font_combo = QFontComboBox()
        self.mono_font_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        current_mono = get_custom_mono_font()
        if current_mono:
            self.mono_font_combo.setCurrentFont(QFont(current_mono))
        layout.addRow("Monospace Font:", self.mono_font_combo)

        # Preview
        self.preview = QLabel("The quick brown fox jumps over the lazy dog\n0123456789 {}[]();:',.")
        self.preview.setStyleSheet(f"padding: 10px; background-color: {COLOR_BG_CARD}; border-radius: 6px;")
        self.preview.setWordWrap(True)
        layout.addRow("Preview:", self.preview)

        # Live preview updates
        self.size_spin.valueChanged.connect(self._update_preview)
        self.ui_font_combo.currentFontChanged.connect(self._update_preview)
        self._update_preview()

        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset)
        layout.addRow("", reset_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _update_preview(self):
        size = self.size_spin.value()
        font = self.ui_font_combo.currentFont()
        font.setPointSize(size)
        self.preview.setFont(font)

    def _reset(self):
        self.size_spin.setValue(10)
        self.ui_font_combo.setCurrentFont(QFont("Segoe UI"))
        self.mono_font_combo.setCurrentFont(QFont("Consolas"))

    def get_settings(self) -> tuple[int, str, str]:
        return (
            self.size_spin.value(),
            self.ui_font_combo.currentFont().family(),
            self.mono_font_combo.currentFont().family(),
        )



# ──────────────────────────────────────────────
# Tutorial / Welcome Dialog
# ──────────────────────────────────────────────

TUTORIAL_PAGES = [
    {
        "title": "Welcome to OpenBL3CMM!",
        "body": (
            "OpenBL3CMM is a hotfix mod manager for Borderlands 3.\n\n"
            "It lets you create, edit, and organize .bl3hotfix and .blmod files "
            "that modify the game via hotfix injection (using OHL or B3HM).\n\n"
            "This quick tutorial will walk you through the basics."
        ),
    },
    {
        "title": "Creating & Opening Files",
        "body": (
            "• File → New  creates a blank mod file\n"
            "• File → Open  loads an existing .bl3hotfix or .blmod\n"
            "• File → Save / Save As  exports your work\n\n"
            "The app auto-saves a backup before each save, stored in:\n"
            "  %APPDATA%/OpenBL3CMM/backups/"
        ),
    },
    {
        "title": "Categories & Entries",
        "body": (
            "Mods are organized into categories (folders) containing hotfix entries.\n\n"
            "• Use the toolbar  + Category  to add a new category\n"
            "• Use  + Entry  (or press Insert) to add a hotfix\n"
            "• Entries can be written in Simple format:\n"
            "    set /Game/Path/Object.Object Property Value\n"
            "• Or pasted as raw Spark format:\n"
            "    SparkPatchEntry,(1,1,0,),/Game/...\n\n"
            "Drag and drop to reorder entries and categories."
        ),
    },
    {
        "title": "Enable / Disable & Color Coding",
        "body": (
            "Each entry has a checkbox to enable or disable it.\n"
            "Disabled entries are commented out in the file (prefixed with #).\n\n"
            "Entries are color-coded by command type:\n"
            "  Blue = set  |  Green = edit  |  Cyan = early_set\n"
            "  Purple = merge  |  Yellow = clone  |  Pink = delete\n\n"
            "You can customize colors in  Preferences → Command Color Coding."
        ),
    },
    {
        "title": "Object Explorer",
        "body": (
            "Press Ctrl+E to open the Object Explorer — a searchable browser\n"
            "of BL3 game objects from a datapack.\n\n"
            "To generate a datapack, go to  Tools → Object Explorer,\n"
            "then click Generate Datapack and point it at your BL3 data.\n\n"
            "The explorer shows object properties, links, and lets you\n"
            "copy paths directly into your hotfix entries."
        ),
    },
    {
        "title": "Tips & Shortcuts",
        "body": (
            "• Double-click an entry to edit it\n"
            "• Ctrl+C / Ctrl+V to copy/paste entries\n"
            "• Ctrl+B to enable, Ctrl+D to disable selected\n"
            "• Ctrl+R to rename a category\n"
            "• Right-click for context menu\n\n"
            "Customize shortcuts in  Preferences → Keyboard Shortcuts.\n\n"
            "You can view this tutorial again from  Help → Tutorial."
        ),
    },
]


class TutorialDialog(QDialog):
    """Multi-page tutorial walkthrough."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenBL3CMM Tutorial")
        self.resize(520, 380)
        self._page = 0

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self._title)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setStyleSheet("font-size: 10pt; line-height: 1.4;")
        self._body.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._body, 1)

        # Page indicator
        self._page_label = QLabel()
        self._page_label.setStyleSheet("color: #888; font-size: 9pt;")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._page_label)

        # Buttons
        btn_layout = QHBoxLayout()

        self._skip_check = QCheckBox("Don't show on startup")
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._skip_check.setChecked(s.value("skip_tutorial", False, type=bool))
        btn_layout.addWidget(self._skip_check)

        btn_layout.addStretch()

        self._btn_back = QPushButton("← Back")
        self._btn_back.clicked.connect(self._go_back)
        btn_layout.addWidget(self._btn_back)

        self._btn_next = QPushButton("Next →")
        self._btn_next.clicked.connect(self._go_next)
        btn_layout.addWidget(self._btn_next)

        self._btn_close = QPushButton("Close")
        self._btn_close.clicked.connect(self._finish)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

        self._update_page()

    def _update_page(self):
        page = TUTORIAL_PAGES[self._page]
        self._title.setText(page["title"])
        self._body.setText(page["body"])
        self._page_label.setText(f"Page {self._page + 1} of {len(TUTORIAL_PAGES)}")
        self._btn_back.setEnabled(self._page > 0)
        is_last = self._page == len(TUTORIAL_PAGES) - 1
        self._btn_next.setVisible(not is_last)
        self._btn_close.setVisible(is_last)

    def _go_back(self):
        if self._page > 0:
            self._page -= 1
            self._update_page()

    def _go_next(self):
        if self._page < len(TUTORIAL_PAGES) - 1:
            self._page += 1
            self._update_page()

    def _finish(self):
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        s.setValue("skip_tutorial", self._skip_check.isChecked())
        self.accept()


# ──────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# Drag & Drop Tree Widget
# ──────────────────────────────────────────────

class DragDropTreeWidget(QTreeWidget):
    """QTreeWidget with drag-and-drop reordering that syncs to the data model."""

    items_moved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._drag_refs = []

    def mousePressEvent(self, event):
        """Deselect everything when clicking empty space."""
        item = self.itemAt(event.position().toPoint())
        if item is None:
            self.clearSelection()
            self.setCurrentItem(None)
            self.itemSelectionChanged.emit()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """Check for custom wheel shortcuts before default scroll."""
        mods = event.modifiers()
        delta = event.angleDelta().y()

        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")

        if delta > 0:
            parts.append("WheelUp")
        elif delta < 0:
            parts.append("WheelDown")

        if parts:
            combo = "+".join(parts)
            shortcuts = get_shortcuts()
            for name, key in shortcuts.items():
                if key == combo:
                    win = self.window()
                    if name == "Zoom In" and hasattr(win, '_change_font_size'):
                        win._change_font_size(1)
                        event.accept()
                        return
                    elif name == "Zoom Out" and hasattr(win, '_change_font_size'):
                        win._change_font_size(-1)
                        event.accept()
                        return

        super().wheelEvent(event)

    def startDrag(self, supportedActions):
        """Capture data model refs before Qt starts the drag."""
        self._drag_refs = []
        for item in self.selectedItems():
            data = item.data(0, ROLE_DATA)
            if data is not None:
                self._drag_refs.append(data)
        # Let Qt handle the visual drag (ghost cursor, drop indicator)
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        """Intercept the drop, update only the data model, then rebuild the tree."""
        # Grab drop info before consuming the event
        drop_pos = self.dropIndicatorPosition()
        target_item = self.itemAt(event.position().toPoint())

        # Always consume — never let Qt's default handler modify tree items
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()

        if not self._drag_refs or not target_item:
            self._drag_refs = []
            return

        target_data = target_item.data(0, ROLE_DATA)
        if target_data is None:
            self._drag_refs = []
            return

        drag_data = list(self._drag_refs)
        self._drag_refs = []

        root = self.window().mod.root if hasattr(self.window(), 'mod') and self.window().mod else None
        if not root:
            return

        has_entries = any(isinstance(d, HotfixEntry) for d in drag_data)

        # Block dropping a category into itself or its descendants
        for d in drag_data:
            if isinstance(d, Category):
                if d is target_data or self._is_descendant_of(target_data, d):
                    return

        # Determine destination parent and index
        dest_parent = None
        dest_index = -1

        if drop_pos == QAbstractItemView.DropIndicatorPosition.OnItem:
            if isinstance(target_data, Category):
                dest_parent = target_data
                dest_index = len(target_data.children)
            else:
                dest_parent = self._find_parent_in(root, target_data)
                if dest_parent:
                    dest_index = self._index_of(dest_parent, target_data) + 1

        elif drop_pos in (QAbstractItemView.DropIndicatorPosition.AboveItem,
                          QAbstractItemView.DropIndicatorPosition.BelowItem):
            target_parent = self._find_parent_in(root, target_data)
            if target_parent is root and has_entries:
                # Entries can't be at root — drop into target category
                if isinstance(target_data, Category):
                    dest_parent = target_data
                    dest_index = 0
                else:
                    return
            elif target_parent:
                dest_parent = target_parent
                dest_index = self._index_of(dest_parent, target_data)
                if drop_pos == QAbstractItemView.DropIndicatorPosition.BelowItem:
                    dest_index += 1

        if dest_parent is None or dest_index < 0:
            return
        if has_entries and dest_parent is root:
            return

        # Remove from old locations — track if removal affects dest_index
        for d in drag_data:
            # If removing from same parent and before dest_index, adjust
            old_parent = self._find_parent_in(root, d)
            if old_parent is dest_parent:
                old_idx = self._index_of(dest_parent, d)
                if old_idx < dest_index:
                    dest_index -= 1
            self._remove_item(root, d)

        # Clean up empty intermediate categories that were just wrappers
        # (don't clean dest_parent itself)

        # Clamp
        if dest_index > len(dest_parent.children):
            dest_index = len(dest_parent.children)

        # Insert
        for i, d in enumerate(drag_data):
            dest_parent.children.insert(dest_index + i, d)
            if isinstance(d, Category):
                d.parent = dest_parent

        self.items_moved.emit()

    # ── Helpers (all use identity comparison) ──

    def _is_descendant_of(self, item_data, ancestor):
        if not isinstance(ancestor, Category):
            return False
        for child in ancestor.children:
            if child is item_data:
                return True
            if isinstance(child, Category) and self._is_descendant_of(item_data, child):
                return True
        return False

    def _find_parent_in(self, cat, target):
        for child in cat.children:
            if child is target:
                return cat
        for child in cat.children:
            if isinstance(child, Category):
                found = self._find_parent_in(child, target)
                if found:
                    return found
        return None

    def _index_of(self, cat, target):
        for i, child in enumerate(cat.children):
            if child is target:
                return i
        return len(cat.children)

    def _remove_item(self, cat, target):
        for i, child in enumerate(cat.children):
            if child is target:
                cat.children.pop(i)
                if isinstance(target, Category):
                    target.parent = None
                return True
        for child in list(cat.children):
            if isinstance(child, Category):
                if self._remove_item(child, target):
                    return True
        return False


# ──────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 750)

        # Set window icon
        icon_path = _get_resource_path("openbl3cmm.ico")
        if icon_path.exists():
            icon = QIcon()
            icon.addFile(str(icon_path))
            self.setWindowIcon(icon)

        self.mod: ModFile | None = None
        self._unsaved = False
        self._updating_tree = False
        self._clipboard: list = []
        self._last_category: Category | None = None  # tracks last selected/highlighted category
        self._open_dialogs: list = []  # prevent GC of non-modal dialogs

        self._build_menu()
        self._build_toolbar()
        self._build_ui()
        self._build_statusbar()
        self._apply_shortcuts()

        # Try to reopen the last file, otherwise start blank
        self._auto_load_last_file()

        # Show tutorial on first launch
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        if not s.value("skip_tutorial", False, type=bool):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self._show_tutorial)

    def _make_independent(self, dlg: QDialog) -> QDialog:
        """Configure a dialog as an independent, non-modal, parentless window."""
        dlg.setParent(None)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.setWindowIcon(self.windowIcon())
        # Track to prevent GC
        self._open_dialogs.append(dlg)
        dlg.destroyed.connect(lambda: self._open_dialogs.remove(dlg) if dlg in self._open_dialogs else None)
        return dlg

    # ── Menu bar ──

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")

        act_new = file_menu.addAction("&New Mod")
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._new_mod)

        act_open = file_menu.addAction("&Open...")
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_file)

        file_menu.addSeparator()

        act_save = file_menu.addAction("&Save")
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._save_file)

        act_saveas = file_menu.addAction("Save &As...")
        act_saveas.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_saveas.triggered.connect(self._save_file_as)

        act_export = file_menu.addAction("&Export Enabled Only...")
        act_export.triggered.connect(self._export_enabled)

        file_menu.addSeparator()

        act_quit = file_menu.addAction("&Quit")
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)

        # Edit
        edit_menu = mb.addMenu("&Edit")

        act_props = edit_menu.addAction("Mod &Properties...")
        act_props.triggered.connect(self._edit_properties)

        edit_menu.addSeparator()

        act_add_cat = edit_menu.addAction("Add &Category")
        act_add_cat.setShortcut("Ctrl+H")
        act_add_cat.triggered.connect(self._add_category_at_root)

        act_add_entry = edit_menu.addAction("Add &Entry")
        act_add_entry.setShortcut("Insert")
        act_add_entry.triggered.connect(self._insert_key_action)

        edit_menu.addSeparator()

        act_enable = edit_menu.addAction("E&nable")
        act_enable.setShortcut("Ctrl+B")
        act_enable.triggered.connect(lambda: self._set_selected_enabled(True))

        act_disable = edit_menu.addAction("&Disable")
        act_disable.setShortcut("Ctrl+D")
        act_disable.triggered.connect(lambda: self._set_selected_enabled(False))

        edit_menu.addSeparator()

        act_copy = edit_menu.addAction("Cop&y")
        act_copy.setShortcut("Ctrl+C")
        act_copy.triggered.connect(self._copy_selected)

        act_cut = edit_menu.addAction("Cu&t")
        act_cut.setShortcut("Ctrl+X")
        act_cut.triggered.connect(self._cut_selected)

        act_paste = edit_menu.addAction("&Paste")
        act_paste.setShortcut("Ctrl+V")
        act_paste.triggered.connect(self._paste)

        edit_menu.addSeparator()

        act_rename = edit_menu.addAction("&Rename Category")
        act_rename.setShortcut("Ctrl+R")
        act_rename.triggered.connect(self._rename_selected_category)

        act_del = edit_menu.addAction("De&lete Selected")
        act_del.setShortcut(QKeySequence.StandardKey.Delete)
        act_del.triggered.connect(self._delete_selected)

        edit_menu.addSeparator()

        act_dirs = edit_menu.addAction("Configure S&hortcuts...")
        act_dirs.triggered.connect(self._configure_shortcuts)

        # View
        view_menu = mb.addMenu("&View")

        act_expand = view_menu.addAction("Expand All")
        act_expand.triggered.connect(lambda: self.tree.expandAll())

        act_collapse = view_menu.addAction("Collapse All")
        act_collapse.triggered.connect(lambda: self.tree.collapseAll())

        view_menu.addSeparator()

        act_zoom_in = view_menu.addAction("Zoom In")
        act_zoom_in.setShortcut("Ctrl+=")
        act_zoom_in.triggered.connect(lambda: self._change_font_size(1))

        act_zoom_out = view_menu.addAction("Zoom Out")
        act_zoom_out.setShortcut("Ctrl+-")
        act_zoom_out.triggered.connect(lambda: self._change_font_size(-1))

        act_zoom_reset = view_menu.addAction("Reset Zoom")
        act_zoom_reset.setShortcut("Ctrl+0")
        act_zoom_reset.triggered.connect(lambda: self._set_font_size(10))

        # Preferences
        prefs_menu = mb.addMenu("&Preferences")

        theme_menu = prefs_menu.addMenu("&Theme")
        current_theme = get_current_theme_name()
        for theme_name in THEMES:
            act = theme_menu.addAction(theme_name)
            act.setCheckable(True)
            act.setChecked(theme_name == current_theme)
            act.triggered.connect(lambda checked, tn=theme_name: self._switch_theme(tn))

        act_font = prefs_menu.addAction("Font && Size Settings...")
        act_font.triggered.connect(self._open_font_settings)

        prefs_menu.addSeparator()

        self._act_detail_panel = prefs_menu.addAction("Show Detail Panel")
        self._act_detail_panel.setCheckable(True)
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        show_detail = s.value("show_detail_panel", False, type=bool)
        self._act_detail_panel.setChecked(show_detail)
        self._act_detail_panel.triggered.connect(self._toggle_detail_panel)

        prefs_menu.addSeparator()
        act_shortcuts = prefs_menu.addAction("Keyboard Shortcuts...")
        act_shortcuts.triggered.connect(self._open_shortcut_editor)

        act_colors = prefs_menu.addAction("Command Color Coding...")
        act_colors.triggered.connect(self._open_color_editor)

        # Tools
        tools_menu = mb.addMenu("&Tools")
        act_oe = tools_menu.addAction("&Object Explorer")
        act_oe.setShortcut("Ctrl+E")
        act_oe.triggered.connect(self._open_object_explorer)

        # Help
        help_menu = mb.addMenu("&Help")
        act_tutorial = help_menu.addAction("&Tutorial")
        act_tutorial.triggered.connect(self._show_tutorial)
        help_menu.addSeparator()
        act_about = help_menu.addAction("&About")
        act_about.triggered.connect(self._show_about)

    # ── Toolbar ──

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        tb.addAction("New", self._new_mod)
        tb.addAction("Open", self._open_file)
        tb.addAction("Save", self._save_file)
        tb.addSeparator()
        tb.addAction("+ Category", self._add_category_at_root)
        tb.addAction("+ Entry", self._add_entry_at_root)
        tb.addSeparator()
        tb.addAction("Delete", self._delete_selected)
        tb.addSeparator()

        # Search
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search entries...")
        self.search_box.setMaximumWidth(250)
        self.search_box.textChanged.connect(self._filter_tree)
        tb.addWidget(self.search_box)

    # ── Main UI ──

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # Left: tree view
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.tree = DragDropTreeWidget()
        self.tree.setHeaderLabels(["Name"])
        self.tree.header().setVisible(False)
        self.tree.setColumnWidth(0, 700)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.items_moved.connect(self._on_items_moved)
        left_layout.addWidget(self.tree)

        left.setMinimumWidth(400)
        splitter.addWidget(left)

        # Right: detail panel
        self._right_panel = QWidget()
        self._right_panel.setMaximumWidth(500)
        right_layout = QVBoxLayout(self._right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.detail_label = QLabel("Select an entry to view details")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: bold; font-size: 11pt;")
        right_layout.addWidget(self.detail_label)

        # Info group
        info_group = QGroupBox("Entry Details")
        info_layout = QVBoxLayout(info_group)

        self.detail_comment = QLabel("")
        self.detail_comment.setWordWrap(True)
        self.detail_comment.setStyleSheet(f"color: {COLOR_FG_DIM}; font-style: italic;")
        info_layout.addWidget(self.detail_comment)

        self.detail_type = QLabel("")
        self.detail_type.setWordWrap(True)
        info_layout.addWidget(self.detail_type)

        self.detail_object = QLabel("")
        self.detail_object.setWordWrap(True)
        self.detail_object.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(self.detail_object)

        self.detail_attr = QLabel("")
        self.detail_attr.setWordWrap(True)
        info_layout.addWidget(self.detail_attr)

        right_layout.addWidget(info_group)

        # Raw line
        raw_group = QGroupBox("Command")
        raw_layout = QVBoxLayout(raw_group)
        self.detail_raw = QTextEdit()
        self.detail_raw.setReadOnly(True)
        self.detail_raw.setMaximumHeight(120)
        raw_layout.addWidget(self.detail_raw)
        right_layout.addWidget(raw_group)

        right_layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()

        self.btn_edit = QPushButton("Edit Entry")
        self.btn_edit.clicked.connect(self._edit_selected)
        btn_layout.addWidget(self.btn_edit)

        right_layout.addLayout(btn_layout)

        splitter.addWidget(self._right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # Hide detail panel by default (toggle via Preferences)
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        if not s.value("show_detail_panel", False, type=bool):
            self._right_panel.hide()

    # ── Status bar ──

    def _build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._update_status()

    def _update_status(self):
        if self.mod:
            total = len(self.mod.all_entries())
            enabled = len(self.mod.all_entries(enabled_only=True))
            name = self.mod.name or "Untitled"
            unsaved = " *" if self._unsaved else ""
            self.status.showMessage(
                f"{name}{unsaved}  |  {enabled}/{total} entries enabled  |  "
                f"Author: {self.mod.author or '(none)'}  |  v{self.mod.version or '?'}"
            )
        else:
            self.status.showMessage("No mod loaded")

    # ── Tree population ──

    def _populate_tree(self):
        """Rebuild the tree widget from the current ModFile."""
        was_updating = self._updating_tree
        self._updating_tree = True

        # Save expanded state by category name path
        expanded = self._get_expanded_paths()
        scroll_pos = self.tree.verticalScrollBar().value() if self.tree.verticalScrollBar() else 0

        self.tree.clear()
        if not self.mod:
            self._updating_tree = was_updating
            return

        for child in self.mod.root.children:
            if isinstance(child, Category):
                self._add_category_to_tree(child, self.tree.invisibleRootItem())
            elif isinstance(child, HotfixEntry):
                self._add_entry_to_tree(child, self.tree.invisibleRootItem())

        # Restore expanded state, or default to depth 0 for fresh loads
        if expanded:
            self._restore_expanded_paths(expanded)
        else:
            self.tree.expandToDepth(0)

        # Restore scroll position
        if self.tree.verticalScrollBar():
            self.tree.verticalScrollBar().setValue(scroll_pos)

        self._updating_tree = was_updating
        self._update_status()

    def _get_expanded_paths(self) -> set[str]:
        """Collect name-paths of all expanded category items."""
        paths = set()
        root = self.tree.invisibleRootItem()
        self._collect_expanded(root, [], paths)
        return paths

    def _collect_expanded(self, item: QTreeWidgetItem, path: list[str], out: set):
        for i in range(item.childCount()):
            child = item.child(i)
            data = child.data(0, ROLE_DATA)
            if isinstance(data, Category):
                current_path = path + [data.name]
                if child.isExpanded():
                    out.add("/".join(current_path))
                self._collect_expanded(child, current_path, out)

    def _restore_expanded_paths(self, paths: set[str]):
        """Expand items whose name-paths match the saved set."""
        root = self.tree.invisibleRootItem()
        self._apply_expanded(root, [], paths)

    def _apply_expanded(self, item: QTreeWidgetItem, path: list[str], paths: set):
        for i in range(item.childCount()):
            child = item.child(i)
            data = child.data(0, ROLE_DATA)
            if isinstance(data, Category):
                current_path = path + [data.name]
                key = "/".join(current_path)
                child.setExpanded(key in paths)
                self._apply_expanded(child, current_path, paths)

    def _add_category_to_tree(self, cat: Category, parent_item: QTreeWidgetItem):
        item = QTreeWidgetItem()
        entry_count = cat.entry_count()
        enabled_count = cat.enabled_entry_count()
        item.setText(0, f"{cat.name}  ({enabled_count}/{entry_count})")
        item.setData(0, ROLE_DATA, cat)
        item.setForeground(0, QBrush(QColor(COLOR_CATEGORY)))
        item.setFont(0, self._bold_font())

        # Always show expand arrow even if empty (so you can add children)
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        # Checkbox for categories
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        if enabled_count == 0:
            item.setCheckState(0, Qt.CheckState.Unchecked)
        elif enabled_count == entry_count:
            item.setCheckState(0, Qt.CheckState.Checked)
        else:
            item.setCheckState(0, Qt.CheckState.PartiallyChecked)

        parent_item.addChild(item)

        for child in cat.children:
            if isinstance(child, Category):
                self._add_category_to_tree(child, item)
            elif isinstance(child, HotfixEntry):
                self._add_entry_to_tree(child, item)

    def _add_entry_to_tree(self, entry: HotfixEntry, parent_item: QTreeWidgetItem):
        # If entry has a comment, add a non-interactive label row above it
        if entry.comment:
            comment_item = QTreeWidgetItem()
            comment_text = entry.comment.lstrip("# ").strip()
            comment_item.setText(0, f"# {comment_text}")
            comment_item.setForeground(0, QBrush(QColor("#ffd700")))
            font = QFont()
            font.setItalic(True)
            font.setPointSize(get_font_size())
            comment_item.setFont(0, font)
            # No checkbox, not selectable, not editable
            comment_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            # Link it to the entry so we know it's a comment
            comment_item.setData(0, ROLE_DATA, ("comment_for", entry))
            parent_item.addChild(comment_item)

        item = QTreeWidgetItem()
        item.setText(0, entry.display_name)
        item.setData(0, ROLE_DATA, entry)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if entry.enabled else Qt.CheckState.Unchecked)
        parent_item.addChild(item)
        self._style_entry_item(item, entry)

    def _style_entry_item(self, item: QTreeWidgetItem, entry: HotfixEntry, cat_color: str = None):
        # Check for errors — red overrides everything
        has_error = False
        error_msg = ""
        try:
            from hotfix_highlighter import validate_hotfix
            text = entry.simple_form if entry.simple_form else entry.raw_line
            problems = validate_hotfix(text)
            if problems:
                has_error = True
                error_msg = "; ".join(problems)
        except Exception:
            pass

        if has_error:
            item.setForeground(0, QBrush(QColor("#ff4444")))
            item.setToolTip(0, "Error: " + error_msg)
        else:
            # Color by command type — extract first word
            cmd_type = entry.simple_type.split()[0].lower() if entry.simple_type else ""
            cmd_colors = get_command_colors()
            color = QColor(cmd_colors.get(cmd_type, COLOR_FG))
            if not entry.enabled:
                # Dim the color for disabled entries
                color.setAlpha(90)
            item.setForeground(0, QBrush(color))
            item.setToolTip(0, "")

    def _bold_font(self) -> QFont:
        f = QFont()
        f.setBold(True)
        f.setPointSize(get_font_size())
        return f

    # ── Actions ──

    def _try_load_datapack_for_highlighter(self):
        """Load the saved OE datapack so the syntax highlighter can validate paths."""
        try:
            s = QSettings(SETTINGS_ORG, SETTINGS_APP)
            db_path = s.value("object_explorer_db", "")
            if db_path and Path(db_path).is_file():
                from object_explorer import ObjectExplorerDB
                from hotfix_highlighter import set_datapack
                db = ObjectExplorerDB(db_path)
                set_datapack(db)
        except Exception:
            pass

    def _auto_load_last_file(self):
        """Try to reopen the last file from the previous session."""
        # Also try to load the OE datapack for the syntax highlighter
        self._try_load_datapack_for_highlighter()

        # Check for updates in background
        self._update_version = ""
        self._update_url = ""
        check_for_updates(parent=self)

        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        last_file = s.value("last_opened_file", "")
        if last_file and Path(last_file).is_file():
            try:
                self.mod = parse_file(last_file)
                self._flatten_root()
                self._unsaved = False
                # Load saved expanded state
                saved_expanded = self._load_expanded_state()
                self._updating_tree = True
                self.tree.clear()
                for child in self.mod.root.children:
                    if isinstance(child, Category):
                        self._add_category_to_tree(child, self.tree.invisibleRootItem())
                if saved_expanded:
                    self._restore_expanded_paths(saved_expanded)
                else:
                    self.tree.expandToDepth(0)
                self._updating_tree = False
                self._update_status()
                self.setWindowTitle(f"{APP_NAME} — {self.mod.name}")
                return
            except Exception:
                pass
        # Fallback to blank mod
        self._new_mod()

    def _save_last_file_path(self, path: str):
        """Remember the current file path for next launch."""
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        s.setValue("last_opened_file", path)

    def _new_mod(self):
        if self._unsaved and not self._confirm_discard():
            return
        self.mod = ModFile(name="New Mod", author="", version="0.1.0")
        self._unsaved = False
        self._populate_tree()
        self.setWindowTitle(f"{APP_NAME} — New Mod")

    def _open_file(self):
        if self._unsaved and not self._confirm_discard():
            return

        dlg = ModFileDialog(self, mode="open", caption="Open BL3 Hotfix Mod",
                            filter_str="All Mod Files (*.bl3hotfix *.blmod *.txt);;BL3 Hotfix (*.bl3hotfix);;BLMOD (*.blmod);;Text Files (*.txt);;All Files (*)")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        path = dlg.get_path()
        if not path:
            return

        try:
            self.mod = parse_file(path)
            self._flatten_root()
            self._unsaved = False
            self._populate_tree()
            self.setWindowTitle(f"{APP_NAME} — {self.mod.name}")
            self._save_last_file_path(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse file:\n{e}")

    def _save_file(self):
        if not self.mod:
            return
        if self.mod.file_path:
            self._do_save(self.mod.file_path)
        else:
            self._save_file_as()

    def _save_file_as(self):
        if not self.mod:
            return
        default_name = self.mod.name.replace(" ", "_") + ".blmod"
        dlg = ModFileDialog(self, mode="save", caption="Save BL3 Hotfix Mod",
                            default_name=default_name,
                            filter_str="BLMOD Files (*.blmod);;BL3 Hotfix (*.bl3hotfix);;Text Files (*.txt);;All Files (*)")
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.get_path():
            self._do_save(dlg.get_path())

    def _do_save(self, path: str):
        try:
            # Backup existing file before overwriting
            if Path(path).exists():
                backup_mod_file(path)
            export_to_file(self.mod, path)
            self.mod.file_path = path
            self._unsaved = False
            self._update_status()
            self.setWindowTitle(f"{APP_NAME} — {self.mod.name}")
            self._save_last_file_path(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def _export_enabled(self):
        if not self.mod:
            return
        default_name = self.mod.name.replace(" ", "_") + "_enabled.blmod"
        dlg = ModFileDialog(self, mode="save", caption="Export Enabled Entries Only",
                            default_name=default_name,
                            filter_str="BLMOD Files (*.blmod);;BL3 Hotfix (*.bl3hotfix);;Text Files (*.txt);;All Files (*)")
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.get_path():
            try:
                export_to_file(self.mod, dlg.get_path(), enabled_only=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def _edit_properties(self):
        if not self.mod:
            return
        dlg = self._make_independent(MetadataDialog(self.mod, self))

        def on_accepted():
            dlg.apply()
            self._mark_unsaved()
            self.setWindowTitle(f"{APP_NAME} — {self.mod.name}")

        dlg.accepted.connect(on_accepted)
        dlg.show()

    def _add_category_at_root(self):
        """Add a new category at the top level (toolbar / menu bar)."""
        if not self.mod:
            return
        name, ok = QInputDialog.getText(self, "New Category", "Category name:")
        if not ok or not name.strip():
            return
        new_cat = Category(name=name.strip())
        self.mod.root.add_child(new_cat)
        self._mark_unsaved()
        self._populate_tree()

    def _add_category_contextual(self):
        """Add a new subcategory inside the selected category (right-click)."""
        if not self.mod:
            return
        name, ok = QInputDialog.getText(self, "New Subcategory", "Category name:")
        if not ok or not name.strip():
            return
        new_cat = Category(name=name.strip())

        sel = self.tree.currentItem()
        if sel:
            data = sel.data(0, ROLE_DATA)
            if isinstance(data, Category):
                data.add_child(new_cat)
            elif isinstance(data, HotfixEntry):
                parent_item = sel.parent()
                if parent_item:
                    parent_data = parent_item.data(0, ROLE_DATA)
                    if isinstance(parent_data, Category):
                        parent_data.add_child(new_cat)
                    else:
                        self.mod.root.add_child(new_cat)
                else:
                    self.mod.root.add_child(new_cat)
            else:
                self.mod.root.add_child(new_cat)
        else:
            self.mod.root.add_child(new_cat)

        self._mark_unsaved()
        self._populate_tree()

    def _add_entry_at_root(self):
        """Add a new entry to the last highlighted category, or at root level."""
        if not self.mod:
            return
        dlg = self._make_independent(NewEntryDialog(self))

        def on_accepted():
            entry = dlg.get_entry()
            if not entry:
                return
            target = self._last_category
            if target is None:
                # No category ever selected — add directly to root
                self.mod.root.add_child(entry)
            else:
                target.add_child(entry)
            self._mark_unsaved()
            self._populate_tree()
            self._active_dialog = None

        dlg.accepted.connect(on_accepted)
        dlg.rejected.connect(lambda: setattr(self, '_active_dialog', None))
        dlg.show()

    def _add_entry_contextual(self):
        """Add a new entry inside the selected category (right-click / Insert)."""
        if not self.mod:
            return

        # Capture target category NOW, before the dialog opens
        target: Category | None = None
        sel = self.tree.currentItem()
        if sel:
            data = sel.data(0, ROLE_DATA)
            if isinstance(data, Category):
                target = data
            elif isinstance(data, HotfixEntry):
                parent_item = sel.parent()
                if parent_item:
                    target = parent_item.data(0, ROLE_DATA)
        if target is None:
            target = self._last_category

        dlg = self._make_independent(NewEntryDialog(self))

        def on_accepted():
            entry = dlg.get_entry()
            if not entry:
                return
            if target is not None:
                target.add_child(entry)
            else:
                self.mod.root.add_child(entry)
            self._mark_unsaved()
            self._populate_tree()

        dlg.accepted.connect(on_accepted)
        dlg.show()

    def _toggle_selected(self):
        items = self.tree.selectedItems()
        if not items:
            return

        for item in items:
            data = item.data(0, ROLE_DATA)
            if isinstance(data, HotfixEntry):
                data.enabled = not data.enabled
                self._style_entry_item(item, data)
            elif isinstance(data, Category):
                # Toggle all entries in category
                self._toggle_category(data)

        self._mark_unsaved()
        self._populate_tree()

    def _toggle_category(self, cat: Category):
        """Toggle all entries: if any are enabled, disable all; else enable all."""
        entries = []
        self.mod._collect_entries(cat, entries, False)
        any_enabled = any(e.enabled for e in entries)
        for e in entries:
            e.enabled = not any_enabled

    def _delete_selected(self):
        items = self.tree.selectedItems()
        if not items:
            return

        count = len(items)
        reply = QMessageBox.question(
            self, "Delete",
            f"Delete {count} selected item(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for item in items:
            data = item.data(0, ROLE_DATA)
            if isinstance(data, HotfixEntry):
                self._remove_entry_from_model(data)
            elif isinstance(data, Category):
                self._remove_category_from_model(data)

        self._mark_unsaved()
        self._populate_tree()

    def _remove_entry_from_model(self, entry: HotfixEntry):
        """Remove an entry from wherever it lives in the tree."""
        self._remove_from_parent(self.mod.root, entry)

    def _remove_category_from_model(self, cat: Category):
        if cat.parent:
            cat.parent.remove_child(cat)
        else:
            self.mod.root.remove_child(cat)

    def _remove_from_parent(self, cat: Category, target) -> bool:
        for i, child in enumerate(cat.children):
            if child is target:
                cat.children.pop(i)
                return True
        for child in list(cat.children):
            if isinstance(child, Category):
                if self._remove_from_parent(child, target):
                    return True
        return False

    def _insert_key_action(self):
        """Insert key: edit if entry is selected, add new entry otherwise."""
        item = self.tree.currentItem()
        if item:
            data = item.data(0, ROLE_DATA)
            if isinstance(data, HotfixEntry):
                self._edit_selected()
                return
        self._add_entry_contextual()

    def _edit_selected(self):
        item = self.tree.currentItem()
        if not item:
            return
        data = item.data(0, ROLE_DATA)
        if isinstance(data, HotfixEntry):
            # Check if this entry already has an open editor
            if not hasattr(self, '_entry_editors'):
                self._entry_editors: dict[int, QDialog] = {}
            entry_id = id(data)
            if entry_id in self._entry_editors:
                existing = self._entry_editors[entry_id]
                existing.raise_()
                existing.activateWindow()
                return

            dlg = self._make_independent(EditEntryDialog(data, self))
            self._entry_editors[entry_id] = dlg

            def on_accepted():
                dlg.apply()
                self._mark_unsaved()
                self._populate_tree()
                self._entry_editors.pop(entry_id, None)

            def on_closed():
                self._entry_editors.pop(entry_id, None)

            dlg.accepted.connect(on_accepted)
            dlg.rejected.connect(on_closed)
            dlg.destroyed.connect(on_closed)
            dlg.show()

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, ROLE_DATA)
        if isinstance(data, HotfixEntry):
            self._edit_selected()
        # Categories: let Qt handle expand/collapse naturally, rename via right-click only

    def _rename_category(self, item: QTreeWidgetItem):
        data = item.data(0, ROLE_DATA)
        if isinstance(data, Category):
            name, ok = QInputDialog.getText(
                self, "Rename Category", "New name:", text=data.name
            )
            if ok and name.strip():
                data.name = name.strip()
                self._mark_unsaved()
                self._populate_tree()

    def _rename_selected_category(self):
        item = self.tree.currentItem()
        if item:
            self._rename_category(item)

    def _on_selection_changed(self):
        item = self.tree.currentItem()
        if not item:
            self._clear_detail()
            return

        data = item.data(0, ROLE_DATA)

        # If clicked on a comment row, show the linked entry's details
        if isinstance(data, tuple) and len(data) == 2 and data[0] == "comment_for":
            entry = data[1]
            if isinstance(entry, HotfixEntry):
                self.detail_label.setText(entry.display_name)
                self.detail_comment.setText(entry.comment if entry.comment else "(no comment)")
                self.detail_type.setText(f"Type: {entry.simple_type}")
                self.detail_object.setText(f"Object: {entry.object_path}")
                self.detail_attr.setText(f"Attribute: {entry.attribute}")
                self.detail_raw.setPlainText(entry.simple_form)
            return

        # Track the last selected category (or parent category of selected entry)
        if isinstance(data, Category):
            self._last_category = data
        elif isinstance(data, HotfixEntry):
            parent_item = item.parent()
            if parent_item:
                parent_data = parent_item.data(0, ROLE_DATA)
                if isinstance(parent_data, Category):
                    self._last_category = parent_data

        if isinstance(data, HotfixEntry):
            self.detail_label.setText(data.display_name)
            self.detail_comment.setText(data.comment if data.comment else "(no comment)")
            self.detail_type.setText(f"Type: {data.simple_type}")
            self.detail_object.setText(f"Object: {data.object_path}")
            self.detail_attr.setText(f"Attribute: {data.attribute}")
            self.detail_raw.setPlainText(data.simple_form)
        elif isinstance(data, Category):
            total = data.entry_count()
            enabled = data.enabled_entry_count()
            sub_count = sum(1 for c in data.children if isinstance(c, Category))
            self.detail_label.setText(data.name)
            self.detail_comment.setText(
                f"{total} entries ({enabled} enabled), {sub_count} subcategories"
            )
            self.detail_type.setText("Category")
            self.detail_object.setText("")
            self.detail_attr.setText("")
            self.detail_raw.clear()

    def _on_items_moved(self):
        """Called after a drag-drop reorder. Rebuild the tree from the updated model."""
        self._mark_unsaved()
        self._populate_tree()

    def _flatten_root(self):
        """Flatten nested 'root' wrappers in the model (only on load)."""
        if not self.mod:
            return
        root = self.mod.root
        while (len(root.children) == 1
               and isinstance(root.children[0], Category)
               and root.children[0].name.lower() == "root"):
            inner = root.children[0]
            root.children = inner.children
            for c in root.children:
                if isinstance(c, Category):
                    c.parent = root

    def _show_update_available(self):
        """Show update available dialog with option to auto-update."""
        version = getattr(self, '_update_version', '')
        url = getattr(self, '_update_url', '')
        installer_url = getattr(self, '_update_installer_url', '')
        if not version:
            return

        msg = (
            f"A new version of {APP_NAME} is available!\n\n"
            f"Current: {APP_VERSION}\n"
            f"Latest: {version}\n\n"
        )

        if installer_url:
            msg += "Would you like to download and install the update now?"
            reply = QMessageBox.question(
                self, "Update Available", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._download_and_install_update(installer_url, version)
        else:
            msg += "Would you like to open the download page?"
            reply = QMessageBox.question(
                self, "Update Available", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes and url:
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))

    def _download_and_install_update(self, installer_url: str, version: str):
        """Download the installer and run it."""
        from PySide6.QtWidgets import QProgressDialog
        import tempfile

        # Create progress dialog
        progress = QProgressDialog(
            f"Downloading {APP_NAME} {version}...", "Cancel", 0, 100, self
        )
        progress.setWindowTitle("Updating")
        progress.setMinimumWidth(400)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setValue(0)
        progress.show()

        # Download in background thread
        import threading
        self._update_download_path = None
        self._update_download_error = None
        self._update_download_progress = 0
        self._update_download_done = False
        self._update_cancelled = False

        progress.canceled.connect(lambda: setattr(self, '_update_cancelled', True))

        temp_dir = tempfile.gettempdir()
        filename = installer_url.split("/")[-1]
        dest_path = Path(temp_dir) / filename

        def _download():
            try:
                import urllib.request
                req = urllib.request.Request(
                    installer_url,
                    headers={"User-Agent": "OpenBL3CMM", "Accept": "application/octet-stream"}
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 65536

                    with open(str(dest_path), 'wb') as f:
                        while True:
                            if self._update_cancelled:
                                self._update_download_error = "Cancelled"
                                return
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                self._update_download_progress = int(downloaded * 100 / total)

                self._update_download_path = str(dest_path)
            except Exception as e:
                self._update_download_error = str(e)
            finally:
                self._update_download_done = True

        t = threading.Thread(target=_download, daemon=True)
        t.start()

        # Poll progress from main thread
        from PySide6.QtCore import QTimer

        def _poll():
            if self._update_cancelled:
                progress.close()
                return

            progress.setValue(self._update_download_progress)

            if not self._update_download_done:
                QTimer.singleShot(100, _poll)
                return

            progress.close()

            if self._update_download_error:
                if self._update_download_error != "Cancelled":
                    QMessageBox.warning(
                        self, "Update Failed",
                        f"Failed to download update:\n{self._update_download_error}\n\n"
                        f"You can download it manually from the releases page."
                    )
                    url = getattr(self, '_update_url', '')
                    if url:
                        from PySide6.QtGui import QDesktopServices
                        QDesktopServices.openUrl(QUrl(url))
                return

            if self._update_download_path:
                self._run_installer(self._update_download_path)

        QTimer.singleShot(100, _poll)

    def _run_installer(self, installer_path: str):
        """Launch the downloaded installer and close the app."""
        reply = QMessageBox.information(
            self, "Update Ready",
            f"Update downloaded successfully!\n\n"
            f"The installer will now run. {APP_NAME} will close.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        import subprocess

        try:
            # Launch installer with /SILENT — shows progress but no questions
            # /CLOSEAPPLICATIONS tells it to close running instances
            subprocess.Popen(
                [installer_path, '/SILENT', '/CLOSEAPPLICATIONS'],
                shell=False,
            )
            # Save state and exit
            self._save_expanded_state()
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to launch installer:\n{e}\n\n"
                f"The installer was saved to:\n{installer_path}\n"
                f"You can run it manually."
            )

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Sync checkbox state back to the data model."""
        if column != 0 or self._updating_tree:
            return

        data = item.data(0, ROLE_DATA)
        if isinstance(data, HotfixEntry):
            new_enabled = item.checkState(0) == Qt.CheckState.Checked
            if data.enabled != new_enabled:
                data.enabled = new_enabled
                self._style_entry_item(item, data)
                self._mark_unsaved()
                # Update parent category labels
                self._updating_tree = True
                self.tree.blockSignals(True)
                self._refresh_category_labels()
                self.tree.blockSignals(False)
                self._updating_tree = False

        elif isinstance(data, Category):
            # Category checkbox toggled — apply to all child entries
            checked = item.checkState(0) != Qt.CheckState.Unchecked
            self._set_category_enabled(data, checked)
            self._mark_unsaved()
            # Update child checkboxes in-place instead of full rebuild
            self._updating_tree = True
            self.tree.blockSignals(True)
            self._sync_children_checkboxes(item, checked)
            self._refresh_category_labels()
            self.tree.blockSignals(False)
            self._updating_tree = False

    def _sync_children_checkboxes(self, item: QTreeWidgetItem, checked: bool):
        """Recursively sync checkbox states of all children to match the data model."""
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_data = child_item.data(0, ROLE_DATA)
            if isinstance(child_data, HotfixEntry):
                child_item.setCheckState(
                    0, Qt.CheckState.Checked if child_data.enabled else Qt.CheckState.Unchecked
                )
                self._style_entry_item(child_item, child_data)
            elif isinstance(child_data, Category):
                self._sync_children_checkboxes(child_item, checked)

    def _deferred_rebuild(self):
        """Rebuild the tree after the current event is fully processed."""
        self.tree.blockSignals(True)
        self._updating_tree = True
        self._populate_tree()
        self._updating_tree = False
        self.tree.blockSignals(False)

    def _set_category_enabled(self, cat: Category, enabled: bool):
        """Recursively enable/disable all entries in a category."""
        for child in cat.children:
            if isinstance(child, HotfixEntry):
                child.enabled = enabled
            elif isinstance(child, Category):
                self._set_category_enabled(child, enabled)

    def _refresh_category_labels(self):
        """Update category item labels with current enabled counts without full rebuild."""
        root = self.tree.invisibleRootItem()
        self._refresh_category_labels_recursive(root)

    def _refresh_category_labels_recursive(self, item: QTreeWidgetItem):
        for i in range(item.childCount()):
            child_item = item.child(i)
            data = child_item.data(0, ROLE_DATA)
            if isinstance(data, Category):
                entry_count = data.entry_count()
                enabled_count = data.enabled_entry_count()
                child_item.setText(0, f"{data.name}  ({enabled_count}/{entry_count})")
                if enabled_count == 0:
                    child_item.setCheckState(0, Qt.CheckState.Unchecked)
                elif enabled_count == entry_count:
                    child_item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    child_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
                self._refresh_category_labels_recursive(child_item)

    def _clear_detail(self):
        self.detail_label.setText("Select an entry to view details")
        self.detail_comment.setText("")
        self.detail_type.setText("")
        self.detail_object.setText("")
        self.detail_attr.setText("")
        self.detail_raw.clear()

    # ── Search / Filter ──

    def _filter_tree(self, text: str):
        """Show/hide tree items based on search text."""
        text = text.strip().lower()
        root = self.tree.invisibleRootItem()

        if not text:
            self._show_all(root)
            return

        self._filter_item(root, text)

    def _filter_item(self, item: QTreeWidgetItem, text: str) -> bool:
        """Returns True if this item or any child matches."""
        if item is self.tree.invisibleRootItem():
            any_match = False
            for i in range(item.childCount()):
                if self._filter_item(item.child(i), text):
                    any_match = True
            return any_match

        data = item.data(0, ROLE_DATA)
        self_matches = False

        if isinstance(data, HotfixEntry):
            self_matches = (
                text in data.display_name.lower()
                or text in data.simple_form.lower()
                or text in data.raw_line.lower()
                or text in data.comment.lower()
            )
        elif isinstance(data, Category):
            self_matches = text in data.name.lower()

        child_matches = False
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), text):
                child_matches = True

        visible = self_matches or child_matches
        item.setHidden(not visible)

        if child_matches:
            item.setExpanded(True)

        return visible

    def _show_all(self, item: QTreeWidgetItem):
        item.setHidden(False)
        for i in range(item.childCount()):
            self._show_all(item.child(i))

    # ── Context menu ──

    def _tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu(self)

        if item:
            data = item.data(0, ROLE_DATA)
            if isinstance(data, HotfixEntry):
                menu.addAction("Edit Entry", self._edit_selected)
                menu.addSeparator()

                act_enable = menu.addAction("Enable")
                act_enable.setShortcut("Ctrl+B")
                act_enable.triggered.connect(lambda: self._set_selected_enabled(True))

                act_disable = menu.addAction("Disable")
                act_disable.setShortcut("Ctrl+D")
                act_disable.triggered.connect(lambda: self._set_selected_enabled(False))

                menu.addSeparator()

                act_insert = menu.addAction("Insert")
                act_insert.setShortcut("Insert")
                act_insert.triggered.connect(self._add_entry_contextual)

                act_copy = menu.addAction("Copy")
                act_copy.setShortcut("Ctrl+C")
                act_copy.triggered.connect(self._copy_selected)

                act_cut = menu.addAction("Cut")
                act_cut.setShortcut("Ctrl+X")
                act_cut.triggered.connect(self._cut_selected)

                act_paste = menu.addAction("Paste")
                act_paste.setShortcut("Ctrl+V")
                act_paste.triggered.connect(self._paste)
                act_paste.setEnabled(bool(self._clipboard))

                menu.addSeparator()
                menu.addAction("Copy hotfix to clipboard", self._copy_hotfix_to_clipboard)
                menu.addSeparator()
                menu.addAction("Delete", self._delete_selected)

            elif isinstance(data, Category):
                act_rename = menu.addAction("Rename category")
                act_rename.setShortcut("Ctrl+R")
                act_rename.triggered.connect(lambda: self._rename_category(item))

                act_new_cat = menu.addAction("Create new empty category")
                act_new_cat.setShortcut("Ctrl+H")
                act_new_cat.triggered.connect(self._add_category_contextual)

                menu.addAction("Flatten category contents", lambda: self._flatten_category(item))

                menu.addSeparator()

                act_enable = menu.addAction("Enable")
                act_enable.setShortcut("Ctrl+B")
                act_enable.triggered.connect(lambda: self._set_selected_enabled(True))

                act_disable = menu.addAction("Disable")
                act_disable.setShortcut("Ctrl+D")
                act_disable.triggered.connect(lambda: self._set_selected_enabled(False))

                menu.addSeparator()

                act_insert = menu.addAction("Insert")
                act_insert.setShortcut("Insert")
                act_insert.triggered.connect(self._add_entry_contextual)

                act_copy = menu.addAction("Copy")
                act_copy.setShortcut("Ctrl+C")
                act_copy.triggered.connect(self._copy_selected)

                act_cut = menu.addAction("Cut")
                act_cut.setShortcut("Ctrl+X")
                act_cut.triggered.connect(self._cut_selected)

                act_paste = menu.addAction("Paste")
                act_paste.setShortcut("Ctrl+V")
                act_paste.triggered.connect(self._paste)
                act_paste.setEnabled(bool(self._clipboard))

                menu.addSeparator()
                menu.addAction("Sort", lambda: self._sort_category(item))

                menu.addSeparator()
                menu.addAction("Fully expand category", lambda: self._expand_recursive(item, True))
                menu.addAction("Fully collapse category", lambda: self._expand_recursive(item, False))

                menu.addSeparator()
                menu.addAction("Export category as mod", lambda: self._export_category_as_mod(item))
                menu.addAction("Copy modlist to clipboard", lambda: self._copy_modlist_to_clipboard(item))

                menu.addSeparator()
                menu.addAction("Import mod", self._import_mod)

                menu.addSeparator()
                menu.addAction("Delete category", self._delete_selected)
        else:
            menu.addAction("Add Category", self._add_category_at_root)
            menu.addAction("Add Entry", self._add_entry_at_root)
            menu.addSeparator()
            menu.addAction("Import mod", self._import_mod)

        menu.exec(self.tree.mapToGlobal(pos))

    # ── Context menu actions ──

    def _set_selected_enabled(self, enabled: bool):
        """Enable or disable all selected items."""
        items = self.tree.selectedItems()
        if not items:
            return
        self._updating_tree = True
        for item in items:
            data = item.data(0, ROLE_DATA)
            if isinstance(data, HotfixEntry):
                data.enabled = enabled
            elif isinstance(data, Category):
                self._set_category_enabled(data, enabled)
        self._mark_unsaved()
        self._populate_tree()
        self._updating_tree = False

    def _copy_selected(self):
        """Copy selected entries/categories to internal clipboard as snapshots."""
        import copy
        items = self.tree.selectedItems()
        if not items:
            return
        self._clipboard = []
        for item in items:
            data = item.data(0, ROLE_DATA)
            # Store a snapshot (deep copy) immediately, not a reference
            snapshot = self._snapshot(data)
            if snapshot is not None:
                self._clipboard.append(("copy", snapshot))

    def _cut_selected(self):
        """Cut selected entries/categories to internal clipboard."""
        items = self.tree.selectedItems()
        if not items:
            return
        self._clipboard = []
        for item in items:
            data = item.data(0, ROLE_DATA)
            snapshot = self._snapshot(data)
            if snapshot is not None:
                self._clipboard.append(("cut", snapshot))
            # Remove original from model
            if isinstance(data, HotfixEntry):
                self._remove_entry_from_model(data)
            elif isinstance(data, Category):
                self._remove_category_from_model(data)
        self._mark_unsaved()
        self._populate_tree()

    def _snapshot(self, data):
        """Create an independent deep copy of a model item, safe from parent cycles."""
        if isinstance(data, HotfixEntry):
            e = HotfixEntry(
                raw_line=data.raw_line,
                comment=data.comment,
                enabled=data.enabled,
            )
            e._original_cmd = data._original_cmd
            return e
        elif isinstance(data, Category):
            return self._snapshot_category(data)
        return None

    def _snapshot_category(self, cat: Category) -> Category:
        """Recursively copy a category and all its children without parent refs."""
        new_cat = Category(name=cat.name, enabled=cat.enabled, mutually_exclusive=cat.mutually_exclusive)
        for child in cat.children:
            if isinstance(child, HotfixEntry):
                new_entry = HotfixEntry(
                    raw_line=child.raw_line,
                    comment=child.comment,
                    enabled=child.enabled,
                )
                new_entry._original_cmd = child._original_cmd
                new_cat.add_child(new_entry)
            elif isinstance(child, Category):
                new_sub = self._snapshot_category(child)
                new_cat.add_child(new_sub)
        return new_cat

    def _paste(self):
        """Paste entries/categories from internal clipboard into the selected location."""
        if not self._clipboard:
            return

        # Find target category
        target: Category | None = None
        sel = self.tree.currentItem()
        if sel:
            data = sel.data(0, ROLE_DATA)
            if isinstance(data, Category):
                target = data
            elif isinstance(data, HotfixEntry):
                parent_item = sel.parent()
                if parent_item:
                    target = parent_item.data(0, ROLE_DATA)

        if target is None and self.mod:
            for child in reversed(self.mod.root.children):
                if isinstance(child, Category):
                    target = child
                    break
            if target is None:
                target = Category(name="Pasted")
                self.mod.root.add_child(target)

        if target is None:
            return

        for mode, snapshot in self._clipboard:
            # Always paste a fresh copy of the snapshot so multiple pastes work
            fresh = self._snapshot(snapshot)
            if fresh is not None:
                target.add_child(fresh)

        # Clear clipboard if it was a cut operation
        if self._clipboard and self._clipboard[0][0] == "cut":
            self._clipboard.clear()

        self._mark_unsaved()
        self._populate_tree()

    def _copy_hotfix_to_clipboard(self):
        """Copy the raw hotfix line of the selected entry to system clipboard."""
        item = self.tree.currentItem()
        if not item:
            return
        data = item.data(0, ROLE_DATA)
        if isinstance(data, HotfixEntry):
            QApplication.clipboard().setText(data.raw_line)

    def _flatten_category(self, item: QTreeWidgetItem):
        """Move all entries from subcategories into this category directly."""
        data = item.data(0, ROLE_DATA)
        if not isinstance(data, Category):
            return

        def _collect_all_entries(cat: Category) -> list[HotfixEntry]:
            entries = []
            for child in cat.children:
                if isinstance(child, HotfixEntry):
                    entries.append(child)
                elif isinstance(child, Category):
                    entries.extend(_collect_all_entries(child))
            return entries

        all_entries = _collect_all_entries(data)
        data.children = list(all_entries)

        # Make sure this category is expanded so you can see the result
        item.setExpanded(True)
        self._mark_unsaved()
        self._populate_tree()

    def _sort_category(self, item: QTreeWidgetItem):
        """Sort children of a category alphabetically."""
        data = item.data(0, ROLE_DATA)
        if not isinstance(data, Category):
            return
        # Categories first (sorted), then entries (sorted)
        cats = sorted(
            [c for c in data.children if isinstance(c, Category)],
            key=lambda c: c.name.lower()
        )
        entries = sorted(
            [c for c in data.children if isinstance(c, HotfixEntry)],
            key=lambda e: e.display_name.lower()
        )
        data.children = cats + entries
        self._mark_unsaved()
        self._populate_tree()

    def _expand_recursive(self, item: QTreeWidgetItem, expand: bool):
        """Recursively expand or collapse a tree item and all its children."""
        item.setExpanded(expand)
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() > 0:
                self._expand_recursive(child, expand)

    def _export_category_as_mod(self, item: QTreeWidgetItem):
        """Export a single category as a standalone .bl3hotfix file."""
        data = item.data(0, ROLE_DATA)
        if not isinstance(data, Category):
            return

        # Create a temporary ModFile with just this category
        from models import ModFile
        temp_mod = ModFile(
            name=data.name,
            version=self.mod.version if self.mod else "",
            author=self.mod.author if self.mod else "",
        )
        temp_mod.root.add_child(data)

        default_name = data.name.replace(" ", "_") + ".bl3hotfix"
        dlg = ModFileDialog(self, mode="save", caption="Export Category as Mod",
                            default_name=default_name)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.get_path():
            try:
                export_to_file(temp_mod, dlg.get_path())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

        # Remove the temporary parent link
        temp_mod.root.children.clear()

    def _copy_modlist_to_clipboard(self, item: QTreeWidgetItem):
        """Copy all enabled hotfix lines from a category to clipboard."""
        data = item.data(0, ROLE_DATA)
        if not isinstance(data, Category):
            return
        entries = []
        self.mod._collect_entries(data, entries, enabled_only=True)
        lines = [e.raw_line for e in entries]
        QApplication.clipboard().setText("\n".join(lines))

    def _import_mod(self):
        """Import another .bl3hotfix file as a category."""
        dlg = ModFileDialog(self, mode="open", caption="Import Mod")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        path = dlg.get_path()
        if not path:
            return
        try:
            imported = parse_file(path)
            # Add all top-level categories from the imported mod
            for child in imported.root.children:
                if isinstance(child, Category):
                    self.mod.root.add_child(child)
            self._mark_unsaved()
            self._populate_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import:\n{e}")

    # ── Utility ──

    def _mark_unsaved(self):
        self._unsaved = True
        self._update_status()

    def _confirm_discard(self) -> bool:
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _show_about(self):
        QMessageBox.about(
            self, "About",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>A visual hotfix mod editor for Borderlands 3 Made by Ty-Gone.</p>"
            f"<p>Compatible with OpenHotfixLoader (OHL) and B3HM.</p>"
            f"<p>Inspired by BLCMM (Borderlands Community Mod Manager).</p>"
        )

    def _show_tutorial(self):
        """Show the tutorial dialog."""
        dlg = self._make_independent(TutorialDialog(self))
        dlg.show()

    def _configure_shortcuts(self):
        dlg = self._make_independent(ShortcutDirsDialog(self))

        def on_accepted():
            save_shortcuts(dlg.get_shortcuts())

        dlg.accepted.connect(on_accepted)
        dlg.show()

    def _change_font_size(self, delta: int):
        """Increase or decrease font size by delta points."""
        current = get_font_size()
        new_size = max(6, min(24, current + delta))
        set_font_size(new_size)
        self._apply_stylesheet()

    def _set_font_size(self, size: int):
        """Set font size to an exact value."""
        set_font_size(size)
        self._apply_stylesheet()

    def _toggle_detail_panel(self, checked: bool):
        """Show or hide the detail panel."""
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        s.setValue("show_detail_panel", checked)
        if checked:
            self._right_panel.show()
        else:
            self._right_panel.hide()

    def _open_shortcut_editor(self):
        """Open the keyboard shortcuts editor."""
        dlg = self._make_independent(ShortcutEditorDialog(self))

        def on_accepted():
            shortcuts = dlg.get_shortcuts()
            for name, key in shortcuts.items():
                set_shortcut(name, key)
            self._apply_shortcuts()

        dlg.accepted.connect(on_accepted)
        dlg.show()

    def _open_color_editor(self):
        """Open the command color coding editor."""
        dlg = self._make_independent(ColorCodingDialog(self))

        def on_accepted():
            colors = dlg.get_colors()
            for cmd, color in colors.items():
                set_command_color(cmd, color)
            if self.mod:
                self._populate_tree()

        dlg.accepted.connect(on_accepted)
        dlg.show()

    def _apply_shortcuts(self):
        """Apply saved shortcuts to all menu actions."""
        shortcuts = get_shortcuts()
        # Re-apply shortcuts to menu actions by finding them
        mb = self.menuBar()
        for menu in mb.findChildren(QMenu):
            for action in menu.actions():
                text = action.text().replace("&", "").replace("...", "").strip()
                if text in shortcuts:
                    action.setShortcut(shortcuts[text])

    def _open_font_settings(self):
        """Open the font settings dialog."""
        dlg = self._make_independent(FontSettingsDialog(self))

        def on_accepted():
            size, ui_font, mono_font = dlg.get_settings()
            set_font_size(size)
            set_custom_font(ui_font)
            set_custom_mono_font(mono_font)
            self._apply_stylesheet()

        dlg.accepted.connect(on_accepted)
        dlg.show()

    def _open_object_explorer(self):
        """Open the Object Explorer window."""
        from object_explorer import ObjectExplorerDialog
        # Reuse existing window if it's still alive
        if not hasattr(self, '_oe_window') or self._oe_window is None:
            self._oe_window = ObjectExplorerDialog()
        self._oe_window.show()
        self._oe_window.raise_()
        self._oe_window.activateWindow()
        # If OE has a DB loaded, share it with the highlighter
        if self._oe_window.explorer.db:
            from hotfix_highlighter import set_datapack
            set_datapack(self._oe_window.explorer.db)

    def _apply_stylesheet(self):
        """Rebuild and apply the stylesheet with current settings."""
        t = get_theme()
        QApplication.instance().setStyleSheet(build_stylesheet(t))
        self._populate_tree()

    def _switch_theme(self, theme_name: str):
        set_current_theme_name(theme_name)
        t = THEMES[theme_name]

        # Update global color references
        global COLOR_BG, COLOR_BG_ALT, COLOR_BG_CARD, COLOR_FG, COLOR_FG_DIM
        global COLOR_ACCENT, COLOR_ACCENT_DIM, COLOR_ENABLED, COLOR_DISABLED
        global COLOR_CATEGORY, COLOR_SELECTION, COLOR_BORDER, COLOR_HOVER
        COLOR_BG = t["bg"]
        COLOR_BG_ALT = t["bg_alt"]
        COLOR_BG_CARD = t["bg_card"]
        COLOR_FG = t["fg"]
        COLOR_FG_DIM = t["fg_dim"]
        COLOR_ACCENT = t["accent"]
        COLOR_ACCENT_DIM = t["accent_dim"]
        COLOR_ENABLED = t["enabled"]
        COLOR_DISABLED = t["disabled"]
        COLOR_CATEGORY = t["category"]
        COLOR_SELECTION = t["selection"]
        COLOR_BORDER = t["border"]
        COLOR_HOVER = t["hover"]

        self._apply_stylesheet()

        # Rebuild the menu to update the checkmarks
        self.menuBar().clear()
        self._build_menu()

    def closeEvent(self, event):
        if hasattr(self, '_unsaved') and self._unsaved:
            if not self._confirm_discard():
                event.ignore()
                return
        # Save expanded category state for next launch
        self._save_expanded_state()
        event.accept()

    def _save_expanded_state(self):
        """Save which categories are expanded to QSettings."""
        if not hasattr(self, 'tree'):
            return
        expanded = self._get_expanded_paths()
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        s.setValue("expanded_categories", json.dumps(list(expanded)))

    def _load_expanded_state(self) -> set[str] | None:
        """Load saved expanded category state from QSettings."""
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        raw = s.value("expanded_categories", None)
        if raw:
            try:
                paths = json.loads(raw)
                if isinstance(paths, list):
                    return set(paths)
            except (json.JSONDecodeError, TypeError):
                pass
        return None


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def _get_resource_path(filename: str) -> Path:
    """Get path to a resource file, works both in dev and PyInstaller exe."""
    # PyInstaller onefile extracts to a temp folder
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / filename


def check_for_updates(parent=None):
    """Check GitHub releases for a newer version. Runs in background."""
    import threading
    import re as _re

    def _parse_version(v):
        """Parse version into (stage, major, minor, ...) for comparison.
        Stage: 0=alpha, 1=beta, 2=release (no prefix).
        So Alpha-0.1 < Alpha-1.0 < Beta-0.1 < 0.1 < 1.0
        """
        v_lower = v.strip().lower()
        if v_lower.startswith("alpha"):
            stage = 0
        elif v_lower.startswith("beta"):
            stage = 1
        else:
            stage = 2
        num_part = _re.sub(r'^[^0-9]*', '', v).strip()
        if not num_part:
            return None
        try:
            nums = tuple(int(x) for x in num_part.split("."))
            return (stage,) + nums
        except ValueError:
            return None

    def _check():
        try:
            import urllib.request
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "OpenBL3CMM"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                import json as _json
                data = _json.loads(resp.read().decode())
                latest_raw = data.get("tag_name", "")

                lat = _parse_version(latest_raw)
                cur = _parse_version(APP_VERSION)

                if lat and cur and lat > cur and parent:
                    parent._update_version = latest_raw
                    parent._update_url = data.get("html_url", "")

                    # Find installer asset (Setup .exe)
                    parent._update_installer_url = ""
                    assets = data.get("assets", [])
                    for asset in assets:
                        name = asset.get("name", "").lower()
                        if name.endswith(".exe") and "setup" in name:
                            parent._update_installer_url = asset.get("browser_download_url", "")
                            break
                    # Fallback: any .exe asset
                    if not parent._update_installer_url:
                        for asset in assets:
                            name = asset.get("name", "").lower()
                            if name.endswith(".exe"):
                                parent._update_installer_url = asset.get("browser_download_url", "")
                                break
        except Exception:
            pass

    t = threading.Thread(target=_check, daemon=True)
    t.start()

    # Poll after 3 seconds to check if the thread found an update
    from PySide6.QtCore import QTimer
    def _check_result():
        if parent and getattr(parent, '_update_version', ''):
            parent._show_update_available()
    QTimer.singleShot(3000, _check_result)


def backup_mod_file(file_path: str):
    """Create a backup of a mod file in AppData/backups/."""
    try:
        src = Path(file_path)
        if not src.exists():
            return
        backup_dir = get_appdata_dir() / "backups"
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"{src.stem}_{timestamp}{src.suffix}"
        import shutil
        shutil.copy2(str(src), str(dest))

        # Keep only last 20 backups per mod name
        prefix = src.stem
        backups = sorted(
            [f for f in backup_dir.iterdir() if f.stem.startswith(prefix)],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for old in backups[20:]:
            old.unlink()
    except Exception:
        pass


def main():
    # Windows taskbar icon fix
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OpenBL3CMM.OpenBL3CMM.0.1")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet(get_theme()))

    # Set app-wide icon
    icon_path = _get_resource_path("openbl3cmm.ico")
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
    else:
        # Try .png fallback or other locations
        for name in ("openbl3cmm.ico", "openbl3cmm.png"):
            p = Path(__file__).parent / name
            if p.exists():
                icon = QIcon(str(p))
                app.setWindowIcon(icon)
                break

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()