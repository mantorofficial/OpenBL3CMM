"""
Object Explorer for OpenBL3CMM.

Provides a browsable tree of BL3 game objects with properties, values,
and references. Uses a SQLite datapack for object data.

Datapack format (SQLite database):
  Table: objects
    - path TEXT PRIMARY KEY     (e.g. /Game/GameData/Balance/...)
    - class_name TEXT           (e.g. DataTable, BlueprintGeneratedClass)
    - data TEXT                 (JSON blob of properties/values)

  Table: refs
    - source TEXT               (object that references)
    - target TEXT               (object being referenced)

  Table: classes
    - name TEXT PRIMARY KEY     (class name)
    - parent TEXT               (parent class name)

The datapack can be generated from extracted BL3 PAK file JSON data,
or from apocalyptech's bl3refs database.
"""
from __future__ import annotations

import json
import sqlite3
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QFont, QColor, QBrush, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget,
    QTreeWidgetItem, QTextEdit, QTextBrowser, QLineEdit, QLabel, QPushButton,
    QTabWidget, QHeaderView, QAbstractItemView, QApplication,
    QFileDialog, QMessageBox, QComboBox, QGroupBox, QDialog,
)


SETTINGS_ORG = "OpenBL3CMM"
SETTINGS_APP = "BL3"


class ObjectExplorerDB:
    """Interface to the Object Explorer SQLite datapack.

    Supports two schemas:
      1. apocalyptech's bl3refs: tables bl3object(id, name) + bl3refs(from_obj, to_obj)
      2. OpenBL3CMM native: tables objects(path, class_name, data) + refs(source, target)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._detect_schema()

    def _detect_schema(self):
        """Detect which schema the database uses."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor}

        # apocalyptech's bl3refs format
        self.is_bl3refs = "bl3object" in tables and "bl3refs" in tables
        # Native OpenBL3CMM format
        self.has_objects = "objects" in tables
        self.has_refs = "refs" in tables
        self.has_classes = "classes" in tables

        if self.is_bl3refs:
            # Create indexes if missing for performance
            try:
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bl3obj_name ON bl3object(name)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bl3refs_from ON bl3refs(from_obj)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bl3refs_to ON bl3refs(to_obj)")
                self.conn.commit()
            except Exception:
                pass

    def close(self):
        if self.conn:
            self.conn.close()

    # ── Object browsing ──

    def get_top_level_paths(self) -> list[str]:
        """Get unique top-level path segments."""
        table = "bl3object" if self.is_bl3refs else "objects"
        col = "name" if self.is_bl3refs else "path"

        cursor = self.conn.execute(f"""
            SELECT DISTINCT
                CASE
                    WHEN instr(substr({col}, 2), '/') > 0
                    THEN substr({col}, 1, instr(substr({col}, 2), '/') + 1)
                    ELSE {col}
                END as top
            FROM {table}
            WHERE {col} LIKE '/%'
            ORDER BY top
        """)
        return [row["top"] for row in cursor if row["top"]]

    def get_children(self, parent_path: str) -> list[dict]:
        """Get direct children of a path (both folders and leaf objects)."""
        if not parent_path.endswith("/"):
            parent_path += "/"

        table = "bl3object" if self.is_bl3refs else "objects"
        col = "name" if self.is_bl3refs else "path"

        cursor = self.conn.execute(f"""
            SELECT {col} as path FROM {table}
            WHERE {col} LIKE ?
            ORDER BY {col}
        """, (parent_path + "%",))

        results = []
        seen_folders = set()

        for row in cursor:
            path = row["path"]
            relative = path[len(parent_path):]
            if not relative:
                continue

            if "/" in relative:
                folder = relative.split("/")[0]
                if folder not in seen_folders:
                    seen_folders.add(folder)
                    results.append({
                        "path": parent_path + folder,
                        "name": folder,
                        "is_folder": True,
                        "class_name": "",
                    })
            else:
                results.append({
                    "path": path,
                    "name": relative,
                    "is_folder": False,
                    "class_name": "",
                })

        return results

    def get_object(self, path: str) -> dict | None:
        """Get object data by path."""
        if self.is_bl3refs:
            cursor = self.conn.execute(
                "SELECT id, name FROM bl3object WHERE name = ?", (path,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "path": row["name"],
                    "class_name": path.rsplit("/", 1)[-1].split(".")[0] if "." in path.rsplit("/", 1)[-1] else "",
                    "properties": {},
                    "_id": row["id"],
                }
        elif self.has_objects:
            cursor = self.conn.execute(
                "SELECT path, class_name, data FROM objects WHERE path = ?", (path,)
            )
            row = cursor.fetchone()
            if row:
                data = {}
                raw = row["data"]
                if raw:
                    try:
                        # Try as plain JSON string first
                        if isinstance(raw, str):
                            data = json.loads(raw)
                        elif isinstance(raw, bytes):
                            # Try zlib decompression (from generate_datapack)
                            try:
                                import zlib
                                decompressed = zlib.decompress(raw).decode("utf-8")
                                data = json.loads(decompressed)
                            except (zlib.error, UnicodeDecodeError):
                                # Not compressed, try as raw bytes
                                data = json.loads(raw.decode("utf-8", errors="replace"))
                    except (json.JSONDecodeError, Exception):
                        data = {"_raw": str(raw)[:1000]}
                return {
                    "path": row["path"],
                    "class_name": row["class_name"] or "",
                    "properties": data,
                }
        return None

    def search_objects(self, query: str, limit: int = 500) -> list[dict]:
        """Search objects by path substring."""
        table = "bl3object" if self.is_bl3refs else "objects"
        col = "name" if self.is_bl3refs else "path"

        cursor = self.conn.execute(f"""
            SELECT {col} as path FROM {table}
            WHERE {col} LIKE ?
            ORDER BY {col}
            LIMIT ?
        """, (f"%{query}%", limit))
        return [{"path": row["path"], "class_name": ""} for row in cursor]

    def search_by_class(self, class_name: str, limit: int = 500) -> list[dict]:
        """Search objects by class name (only works with native schema)."""
        if self.has_objects:
            cursor = self.conn.execute("""
                SELECT path, class_name FROM objects
                WHERE class_name LIKE ?
                ORDER BY path LIMIT ?
            """, (f"%{class_name}%", limit))
            return [{"path": row["path"], "class_name": row["class_name"] or ""} for row in cursor]
        return []

    def search_in_properties(self, query: str, limit: int = 200) -> list[dict]:
        """Search inside object property data (slower, requires native schema with data)."""
        if not self.has_objects:
            return []

        import zlib
        results = []
        query_lower = query.lower()

        cursor = self.conn.execute(
            "SELECT path, class_name, data FROM objects WHERE data IS NOT NULL"
        )
        for row in cursor:
            if len(results) >= limit:
                break
            raw = row["data"]
            try:
                if isinstance(raw, bytes):
                    try:
                        text = zlib.decompress(raw).decode("utf-8", errors="replace")
                    except zlib.error:
                        text = raw.decode("utf-8", errors="replace")
                elif isinstance(raw, str):
                    text = raw
                else:
                    continue

                if query_lower in text.lower():
                    results.append({
                        "path": row["path"],
                        "class_name": row["class_name"] or "",
                    })
            except Exception:
                continue

        return results

    # ── References ──

    def get_references_from(self, path: str) -> list[str]:
        """Get objects that this object references."""
        if self.is_bl3refs:
            cursor = self.conn.execute("""
                SELECT b.name FROM bl3refs r
                JOIN bl3object a ON r.from_obj = a.id
                JOIN bl3object b ON r.to_obj = b.id
                WHERE a.name = ?
                ORDER BY b.name
            """, (path,))
            return [row["name"] for row in cursor]
        elif self.has_refs:
            cursor = self.conn.execute(
                "SELECT target FROM refs WHERE source = ? ORDER BY target", (path,)
            )
            return [row["target"] for row in cursor]
        return []

    def get_references_to(self, path: str) -> list[str]:
        """Get objects that reference this object."""
        if self.is_bl3refs:
            cursor = self.conn.execute("""
                SELECT a.name FROM bl3refs r
                JOIN bl3object a ON r.from_obj = a.id
                JOIN bl3object b ON r.to_obj = b.id
                WHERE b.name = ?
                ORDER BY a.name
            """, (path,))
            return [row["name"] for row in cursor]
        elif self.has_refs:
            cursor = self.conn.execute(
                "SELECT source FROM refs WHERE target = ? ORDER BY source", (path,)
            )
            return [row["source"] for row in cursor]
        return []

    # ── Classes ──

    def get_all_classes(self) -> list[str]:
        """Get all known class names."""
        if self.has_classes:
            cursor = self.conn.execute("SELECT name FROM classes ORDER BY name")
            return [row["name"] for row in cursor]
        if self.has_objects:
            cursor = self.conn.execute(
                "SELECT DISTINCT class_name FROM objects WHERE class_name IS NOT NULL AND class_name != '' ORDER BY class_name"
            )
            return [row["class_name"] for row in cursor]
        return []

    def get_class_parent(self, class_name: str) -> str | None:
        """Get the parent class of a class."""
        if not self.has_classes:
            return None
        cursor = self.conn.execute(
            "SELECT parent FROM classes WHERE name = ?", (class_name,)
        )
        row = cursor.fetchone()
        return row["parent"] if row else None

    # ── Stats ──

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}
        if self.is_bl3refs:
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM bl3object")
            stats["objects"] = cursor.fetchone()["c"]
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM bl3refs")
            stats["refs"] = cursor.fetchone()["c"]
        else:
            if self.has_objects:
                cursor = self.conn.execute("SELECT COUNT(*) as c FROM objects")
                stats["objects"] = cursor.fetchone()["c"]
            if self.has_refs:
                cursor = self.conn.execute("SELECT COUNT(*) as c FROM refs")
                stats["refs"] = cursor.fetchone()["c"]
            if self.has_classes:
                cursor = self.conn.execute("SELECT COUNT(*) as c FROM classes")
                stats["classes"] = cursor.fetchone()["c"]
        return stats


class ObjectExplorerWidget(QWidget):
    """The Object Explorer panel — can be embedded in the main window or as a dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db: ObjectExplorerDB | None = None
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        # Navigation history
        self._history: list[str] = []
        self._history_idx: int = -1
        self._navigating_history = False

        # Font size for properties
        self._prop_font_size = 11

        self._build_ui()
        self._setup_shortcuts()
        self._try_load_last_db()

    # Default shortcuts: (setting_key, default_key1, default_key2, action_name)
    SHORTCUT_DEFS = [
        ("shortcut_find", "Ctrl+F", "", "Find in Properties"),
        ("shortcut_back", "Alt+Left", "", "Back"),
        ("shortcut_forward", "Alt+Right", "", "Forward"),
        ("shortcut_zoom_in", "Ctrl+=", "Ctrl+Shift+=", "Zoom In"),
        ("shortcut_zoom_out", "Ctrl+-", "", "Zoom Out"),
        ("shortcut_zoom_reset", "Ctrl+0", "", "Reset Zoom"),
        ("shortcut_help", "F1", "", "Show Shortcuts"),
    ]

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts from saved settings."""
        from PySide6.QtGui import QShortcut, QKeySequence

        s = QSettings(SETTINGS_ORG, SETTINGS_APP)

        action_map = {
            "shortcut_find": self._show_find_dialog,
            "shortcut_back": self._go_back,
            "shortcut_forward": self._go_forward,
            "shortcut_zoom_in": self._zoom_in,
            "shortcut_zoom_out": self._zoom_out,
            "shortcut_zoom_reset": self._zoom_reset,
            "shortcut_help": self._show_shortcuts_help,
        }

        for setting_key, default1, default2, _name in self.SHORTCUT_DEFS:
            handler = action_map.get(setting_key)
            if not handler:
                continue
            key1 = s.value(f"{setting_key}_1", default1)
            key2 = s.value(f"{setting_key}_2", default2)
            if key1:
                QShortcut(QKeySequence(key1), self).activated.connect(handler)
            if key2:
                QShortcut(QKeySequence(key2), self).activated.connect(handler)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top bar: nav buttons + search + load datapack
        top = QHBoxLayout()

        self.btn_back = QPushButton("\u25C0")
        self.btn_back.setFixedSize(36, 28)
        self.btn_back.setStyleSheet("font-size: 16pt; padding: 0; margin: 0;")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._go_back)
        top.addWidget(self.btn_back)

        self.btn_forward = QPushButton("\u25B6")
        self.btn_forward.setFixedSize(36, 28)
        self.btn_forward.setStyleSheet("font-size: 16pt; padding: 0; margin: 0;")
        self.btn_forward.setEnabled(False)
        self.btn_forward.clicked.connect(self._go_forward)
        top.addWidget(self.btn_forward)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search objects... (e.g. DamageBalanceScalers)")
        self.search_box.textChanged.connect(self._on_search_text_changed)
        self.search_box.returnPressed.connect(self._do_search)
        top.addWidget(self.search_box, stretch=1)

        self.search_class = QComboBox()
        self.search_class.addItem("All Classes")
        self.search_class.setMinimumWidth(150)
        top.addWidget(self.search_class)

        from PySide6.QtWidgets import QCheckBox
        self.search_props_cb = QCheckBox("Search Properties")
        self.search_props_cb.setToolTip("Also search inside object property data (slower)")
        top.addWidget(self.search_props_cb)

        self.btn_load = QPushButton("Load Datapack...")
        self.btn_load.clicked.connect(self._load_datapack)
        top.addWidget(self.btn_load)

        layout.addLayout(top)

        # Status label
        self.status_label = QLabel("No datapack loaded. Click 'Load Datapack...' to get started.")
        self.status_label.setStyleSheet("color: #a0a0a0; padding: 4px; font-size: 11pt;")
        self.status_label.setFixedHeight(28)
        layout.addWidget(self.status_label)

        # Main splitter: tree on left, details on right — this gets all the space
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: object tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Class"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_context_menu)
        splitter.addWidget(self.tree)

        # Right: detail tabs
        self.tabs = QTabWidget()

        # Properties tab with find bar
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        props_layout.setContentsMargins(0, 0, 0, 0)
        props_layout.setSpacing(0)

        self.prop_view = QTextBrowser()
        self.prop_view.setReadOnly(True)
        self.prop_view.setOpenLinks(False)
        self.prop_view.setOpenExternalLinks(False)
        self.prop_view.setFont(QFont("Consolas", 11))
        props_layout.addWidget(self.prop_view, stretch=1)

        self.tabs.addTab(props_widget, "Properties")

        self._find_dialog = None

        # References tab
        refs_widget = QWidget()
        refs_layout = QVBoxLayout(refs_widget)
        refs_layout.setContentsMargins(4, 4, 4, 4)

        refs_layout.addWidget(QLabel("References FROM this object:"))
        self.refs_from = QTreeWidget()
        self.refs_from.setHeaderLabels(["Object Path"])
        self.refs_from.itemDoubleClicked.connect(self._on_ref_double_clicked)
        refs_layout.addWidget(self.refs_from)

        refs_layout.addWidget(QLabel("References TO this object:"))
        self.refs_to = QTreeWidget()
        self.refs_to.setHeaderLabels(["Object Path"])
        self.refs_to.itemDoubleClicked.connect(self._on_ref_double_clicked)
        refs_layout.addWidget(self.refs_to)

        self.tabs.addTab(refs_widget, "References")

        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        # Give the splitter all available vertical space
        layout.addWidget(splitter, stretch=1)

        # Bottom: path display + copy button — fixed size
        bottom = QHBoxLayout()
        self.path_label = QLineEdit()
        self.path_label.setReadOnly(True)
        self.path_label.setPlaceholderText("Select an object to see its path")
        bottom.addWidget(self.path_label, stretch=1)

        btn_copy = QPushButton("Copy Path")
        btn_copy.clicked.connect(self._copy_path)
        bottom.addWidget(btn_copy)

        btn_copy_full = QPushButton("Copy to Entry")
        btn_copy_full.setToolTip("Copy a ready-to-use set command for this object")
        btn_copy_full.clicked.connect(self._copy_as_entry)
        bottom.addWidget(btn_copy_full)

        layout.addLayout(bottom)

    # ── Datapack loading ──

    def _try_load_last_db(self):
        """Try to load the last used datapack."""
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._json_data_dir = s.value("object_explorer_json_dir", "")
        self._json_archive_path = s.value("object_explorer_json_archive", "")
        self._archive = None
        self._archive_type = None
        self._archive_namelist = None
        self._refs_db: ObjectExplorerDB | None = None
        self._refs_db_path = s.value("object_explorer_refs_db", "")
        last_db = s.value("object_explorer_db", "")
        if last_db and Path(last_db).is_file():
            self._open_db(last_db)
        # Also load refs DB if set
        if self._refs_db_path and Path(self._refs_db_path).is_file():
            try:
                self._refs_db = ObjectExplorerDB(self._refs_db_path)
            except Exception:
                self._refs_db = None

    def _load_datapack(self):
        """Menu to choose what to load or unload."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("Load Datapack...", self._load_any_datapack)
        if self.db or self._refs_db or self._json_archive_path or self._json_data_dir:
            menu.addAction("Unload All", self._unload_all)
        menu.exec(self.btn_load.mapToGlobal(self.btn_load.rect().bottomLeft()))

    def _load_any_datapack(self):
        """Single file dialog that auto-detects the file type."""
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        last_dir = s.value("object_explorer_dir", "")

        path, _ = QFileDialog.getOpenFileName(
            self, "Load Datapack",
            last_dir,
            "All Supported (*.sqlite3 *.sqlite *.db *.zip *.7z);;SQLite (*.sqlite3 *.sqlite *.db);;Archives (*.zip *.7z);;All Files (*)"
        )
        if not path:
            return

        s.setValue("object_explorer_dir", str(Path(path).parent))
        ext = Path(path).suffix.lower()

        if ext in (".sqlite3", ".sqlite", ".db"):
            # Detect if it's a refs db or a data db
            import sqlite3
            try:
                conn = sqlite3.connect(path)
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in cursor}
                conn.close()

                if "bl3object" in tables and "bl3refs" in tables and "objects" not in tables:
                    # Pure refs db — load as refs
                    self._refs_db = ObjectExplorerDB(path)
                    self._refs_db_path = path
                    s.setValue("object_explorer_refs_db", path)
                    stats = self._refs_db.get_stats()

                    if not self.db:
                        # Also use as main DB for browsing
                        s.setValue("object_explorer_db", path)
                        self._open_db(path)
                    else:
                        self._update_status()
                else:
                    # Data db — load as main
                    s.setValue("object_explorer_db", path)
                    self._open_db(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")

        elif ext in (".zip", ".7z"):
            self._json_archive_path = path
            self._json_data_dir = ""
            s.setValue("object_explorer_json_archive", path)
            s.setValue("object_explorer_json_dir", "")
            try:
                if ext == ".7z":
                    import py7zr
                    archive = py7zr.SevenZipFile(path, "r")
                    names = archive.getnames()
                    json_count = sum(1 for n in names if n.endswith(".json"))
                    self._archive = archive
                    self._archive_type = "7z"
                    self._archive_namelist = names
                else:
                    import zipfile
                    archive = zipfile.ZipFile(path, "r")
                    names = archive.namelist()
                    json_count = sum(1 for n in names if n.endswith(".json"))
                    self._archive = archive
                    self._archive_type = "zip"
                    self._archive_namelist = names
                self._update_status()
            except ImportError:
                QMessageBox.critical(self, "Missing Dependency",
                    "py7zr is required for 7z support.\nInstall: pip install py7zr")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open archive:\n{e}")

    def _unload_db(self):
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        if self.db:
            self.db.close()
            self.db = None
        s.setValue("object_explorer_db", "")
        self.tree.clear()
        self._update_status()

    def _unload_json_dir(self):
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._json_data_dir = ""
        s.setValue("object_explorer_json_dir", "")
        self._update_status()

    def _unload_archive(self):
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._json_archive_path = ""
        self._archive = None
        self._archive_type = None
        self._archive_namelist = None
        s.setValue("object_explorer_json_archive", "")
        self._update_status()

    def _unload_refs(self):
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        if self._refs_db:
            self._refs_db.close()
            self._refs_db = None
        self._refs_db_path = ""
        s.setValue("object_explorer_refs_db", "")
        self._update_status()

    def _unload_all(self):
        self._unload_db()
        self._unload_json_dir()
        self._unload_archive()
        self._unload_refs()

    def _update_status(self):
        """Rebuild the status label from current state."""
        parts = []
        if self.db:
            stats = self.db.get_stats()
            db_name = Path(QSettings(SETTINGS_ORG, SETTINGS_APP).value("object_explorer_db", "")).name
            obj_count = stats.get("objects", 0)
            ref_count = stats.get("refs", 0)
            parts.append(f"{db_name}: {obj_count:,} objects, {ref_count:,} refs")
        if self._refs_db:
            stats = self._refs_db.get_stats()
            parts.append(f"Refs: {stats.get('refs', 0):,}")
        if self._json_data_dir:
            parts.append(f"JSON: {Path(self._json_data_dir).name}")
        if self._json_archive_path:
            parts.append(f"Archive: {Path(self._json_archive_path).name}")
        if parts:
            self.status_label.setText("  |  ".join(parts))
        else:
            self.status_label.setText("No datapack loaded. Click 'Load Datapack...' to get started.")

    def _ensure_archive_open(self):
        """Ensure the archive is open if we have one configured."""
        if self._json_archive_path and not self._archive:
            try:
                ext = Path(self._json_archive_path).suffix.lower()
                if ext == ".7z":
                    import py7zr
                    self._archive = py7zr.SevenZipFile(self._json_archive_path, "r")
                    self._archive_type = "7z"
                    self._archive_namelist = self._archive.getnames()
                else:
                    import zipfile
                    self._archive = zipfile.ZipFile(self._json_archive_path, "r")
                    self._archive_type = "zip"
                    self._archive_namelist = self._archive.namelist()
            except Exception:
                self._archive = None

    def _load_json_for_path(self, obj_path: str) -> dict | None:
        """Try to load JSON data from archive or directory."""
        if self._json_archive_path:
            return self._load_json_from_archive(obj_path)
        if self._json_data_dir:
            return self._load_json_from_dir(obj_path)
        return None

    def _read_from_archive(self, entry_name: str) -> dict | None:
        """Read a single JSON file from the archive."""
        try:
            if self._archive_type == "zip":
                data = self._archive.read(entry_name)
                parsed = json.loads(data.decode("utf-8", errors="replace"))
                return {"_source": f"archive:{entry_name}", "_data": parsed}
            elif self._archive_type == "7z":
                # py7zr reads files differently — need to extract to memory
                import io
                self._archive.reset()
                result = self._archive.read([entry_name])
                if entry_name in result:
                    bio = result[entry_name]
                    data = bio.read()
                    parsed = json.loads(data.decode("utf-8", errors="replace"))
                    return {"_source": f"archive:{entry_name}", "_data": parsed}
        except Exception:
            pass
        return None

    def _load_json_from_archive(self, obj_path: str) -> dict | None:
        """Load a JSON file from inside a ZIP or 7z archive."""
        self._ensure_archive_open()
        if not self._archive or not self._archive_namelist:
            return None

        relative = obj_path.lstrip("/")
        # Try exact path matches
        candidates = [
            relative + ".json",
            relative.replace("/", "\\") + ".json",
        ]

        for candidate in candidates:
            if candidate in self._archive_namelist:
                result = self._read_from_archive(candidate)
                if result:
                    return result

        # Fallback: search by filename
        name = obj_path.rsplit("/", 1)[-1]
        target = f"{name}.json"
        for entry in self._archive_namelist:
            if entry.endswith(target):
                result = self._read_from_archive(entry)
                if result:
                    return result

        return None

    def _load_json_from_dir(self, obj_path: str) -> dict | None:
        """Load a JSON file from the data directory."""
        base_dir = Path(self._json_data_dir)
        relative = obj_path.lstrip("/")
        json_path = base_dir / (relative + ".json")
        if json_path.is_file():
            return self._read_json_file(json_path)

        name = obj_path.rsplit("/", 1)[-1]
        for found in base_dir.rglob(f"{name}.json"):
            return self._read_json_file(found)

        return None

    def _read_json_file(self, path: Path) -> dict | None:
        """Read and parse a JSON file."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            return {"_source": str(path), "_data": data}
        except Exception:
            return None

    def _open_db(self, path: str):
        """Open a SQLite database."""
        if self.db:
            self.db.close()

        try:
            self.db = ObjectExplorerDB(path)
            stats = self.db.get_stats()
            parts = []
            if "objects" in stats:
                parts.append(f"{stats['objects']:,} objects")
            if "refs" in stats:
                parts.append(f"{stats['refs']:,} references")
            if "classes" in stats:
                parts.append(f"{stats['classes']:,} classes")

            self.status_label.setText(
                f"Loaded: {Path(path).name}  —  {', '.join(parts)}"
            )

            # Populate class filter
            self.search_class.clear()
            self.search_class.addItem("All Classes")
            for cls in self.db.get_all_classes()[:500]:
                self.search_class.addItem(cls)

            # Populate tree root
            self._populate_root()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load datapack:\n{e}")
            self.db = None

    def _populate_root(self):
        """Populate the tree with top-level paths."""
        self.tree.clear()
        if not self.db:
            return

        # Get top-level folders from the database
        top_paths = self.db.get_top_level_paths()
        if not top_paths:
            # Try getting children of root
            children = self.db.get_children("/")
            for child in children:
                item = self._make_tree_item(child)
                self.tree.addTopLevelItem(item)
            return

        for path in top_paths:
            item = QTreeWidgetItem()
            name = path.strip("/")
            item.setText(0, name)
            item.setText(1, "")
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, True)  # is_folder
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
            )
            self.tree.addTopLevelItem(item)

    def _make_tree_item(self, child_data: dict) -> QTreeWidgetItem:
        """Create a tree item from child data dict."""
        item = QTreeWidgetItem()
        item.setText(0, child_data["name"])
        item.setText(1, child_data.get("class_name", ""))
        item.setData(0, Qt.ItemDataRole.UserRole, child_data["path"])
        item.setData(0, Qt.ItemDataRole.UserRole + 1, child_data.get("is_folder", False))

        if child_data.get("is_folder"):
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
            )
            item.setForeground(0, QBrush(QColor("#6eaaff")))
        else:
            item.setForeground(0, QBrush(QColor("#e0e0e0")))

        return item

    # ── Tree events ──

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Lazy-load children when a folder is expanded."""
        if item.childCount() > 0:
            # Check if it's a placeholder
            first_child = item.child(0)
            if first_child.text(0) != "":
                return  # already loaded

        # Remove placeholder
        item.takeChildren()

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not self.db:
            return

        children = self.db.get_children(path)
        for child_data in children:
            child_item = self._make_tree_item(child_data)
            item.addChild(child_item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Show object details when clicked."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        is_folder = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if not path:
            return

        if is_folder or not self.db:
            self.path_label.setText(path)
            self.prop_view.clear()
            self.refs_from.clear()
            self.refs_to.clear()
            return

        # Use _navigate_to so history is tracked
        self._navigate_to(path)

    def _on_ref_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Navigate to a referenced object when double-clicked."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self._navigate_to(path)

    def _navigate_to(self, path: str):
        """Navigate the tree to a specific object path and show its details."""
        self.path_label.setText(path)

        # Track history
        if not self._navigating_history:
            # Trim forward history
            if self._history_idx < len(self._history) - 1:
                self._history = self._history[:self._history_idx + 1]
            self._history.append(path)
            self._history_idx = len(self._history) - 1
            self._update_nav_buttons()

        if self.db:
            self._show_object_details(path)

    def _go_back(self):
        """Navigate back in history."""
        if self._history_idx > 0:
            self._history_idx -= 1
            self._navigating_history = True
            path = self._history[self._history_idx]
            self.path_label.setText(path)
            if self.db:
                self._show_object_details(path)
            self._navigating_history = False
            self._update_nav_buttons()

    def _go_forward(self):
        """Navigate forward in history."""
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self._navigating_history = True
            path = self._history[self._history_idx]
            self.path_label.setText(path)
            if self.db:
                self._show_object_details(path)
            self._navigating_history = False
            self._update_nav_buttons()

    def _update_nav_buttons(self):
        """Enable/disable back/forward buttons based on history."""
        self.btn_back.setEnabled(self._history_idx > 0)
        self.btn_forward.setEnabled(self._history_idx < len(self._history) - 1)

    def _zoom_in(self):
        self._prop_font_size = min(24, self._prop_font_size + 1)
        self._apply_prop_font()

    def _zoom_out(self):
        self._prop_font_size = max(6, self._prop_font_size - 1)
        self._apply_prop_font()

    def _zoom_reset(self):
        self._prop_font_size = 11
        self._apply_prop_font()

    def _apply_prop_font(self):
        """Apply current font size by re-rendering HTML in all property views."""
        import re
        fs = self._prop_font_size
        font = QFont("Consolas", fs)

        def _update_view(view):
            """Update a single QTextBrowser's HTML font size."""
            view.setFont(font)
            html = view.toHtml()
            if html:
                # Replace font-size in the <pre> style
                html = re.sub(
                    r'font-size:\s*\d+pt',
                    f'font-size: {fs}pt',
                    html
                )
                # Save scroll position
                scrollbar = view.verticalScrollBar()
                scroll_pos = scrollbar.value() if scrollbar else 0
                view.setHtml(html)
                if scrollbar:
                    scrollbar.setValue(scroll_pos)

        # Update main prop_view
        _update_view(self.prop_view)

        # Update all tabs in Dialog
        parent = self.parent()
        if parent and hasattr(parent, 'prop_tabs'):
            for i in range(parent.prop_tabs.count()):
                widget = parent.prop_tabs.widget(i)
                if isinstance(widget, (QTextEdit, QTextBrowser)):
                    _update_view(widget)
                elif hasattr(widget, '_browser'):
                    _update_view(widget._browser)

    def _show_shortcuts_help(self):
        """Show a dialog with all keyboard shortcuts — dual key capture, all editable."""
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)

        from PySide6.QtWidgets import QGridLayout, QDialogButtonBox
        from PySide6.QtGui import QKeySequence

        class KeyCaptureEdit(QLineEdit):
            """Click then press a key combo or mouse button to capture it."""
            def __init__(self, initial_text):
                super().__init__(initial_text)
                self.setReadOnly(True)
                self.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setPlaceholderText("Press keys or mouse...")
                self._capturing = False
                self._default_style = (
                    "font-size: 11pt; font-weight: bold; "
                    "border: 2px solid #555; padding: 4px;"
                )
                self._active_style = (
                    "font-size: 11pt; font-weight: bold; "
                    "border: 2px solid #6eaaff; padding: 4px; "
                    "background-color: #2a2a3a;"
                )
                self.setStyleSheet(self._default_style)

            def keyPressEvent(self, event):
                if not self._capturing:
                    return
                key = event.key()
                if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                    return
                if key == Qt.Key.Key_Escape:
                    self.clear()
                    self._stop_capture()
                    return
                modifiers = event.modifiers()
                seq = QKeySequence(modifiers.value | key)
                self.setText(seq.toString())
                self._stop_capture()

            def mousePressEvent(self, event):
                if self._capturing:
                    # Capture the mouse button
                    btn = event.button()
                    name = {
                        Qt.MouseButton.MiddleButton: "Middle Click",
                        Qt.MouseButton.BackButton: "Mouse Back",
                        Qt.MouseButton.ForwardButton: "Mouse Forward",
                        Qt.MouseButton.ExtraButton1: "Mouse 4",
                        Qt.MouseButton.ExtraButton2: "Mouse 5",
                    }.get(btn)
                    if name:
                        self.setText(name)
                        self._stop_capture()
                        return
                    # Left click while capturing — ignore (used to focus)
                    return
                # First left click — start capturing
                self._capturing = True
                self.setStyleSheet(self._active_style)
                self.setFocus()

            def _stop_capture(self):
                self._capturing = False
                self.setStyleSheet(self._default_style)

            def wheelEvent(self, event):
                if self._capturing:
                    mods = event.modifiers()
                    prefix = ""
                    if mods & Qt.KeyboardModifier.ControlModifier:
                        prefix += "Ctrl+"
                    if mods & Qt.KeyboardModifier.ShiftModifier:
                        prefix += "Shift+"
                    if mods & Qt.KeyboardModifier.AltModifier:
                        prefix += "Alt+"
                    if event.angleDelta().y() > 0:
                        self.setText(f"{prefix}Scroll Up")
                    else:
                        self.setText(f"{prefix}Scroll Down")
                    self._stop_capture()
                    event.accept()
                    return
                super().wheelEvent(event)

            def focusOutEvent(self, event):
                self._capturing = False
                self.setStyleSheet(self._default_style)
                super().focusOutEvent(event)

        dlg = QDialog(self)
        dlg.setWindowTitle("Keyboard Shortcuts")
        dlg.setMinimumWidth(650)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel("Click a field, then press the key combo. Press Esc to clear."))
        layout.addWidget(QLabel(""))

        grid = QGridLayout()
        grid.setSpacing(6)

        # Headers
        for col, text in enumerate(["Action", "Shortcut 1", "Shortcut 2"]):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 10pt; font-weight: bold; color: #888;")
            grid.addWidget(lbl, 0, col)

        edits = []  # (setting_key, edit1, edit2)
        for i, (setting_key, default1, default2, name) in enumerate(self.SHORTCUT_DEFS):
            row = i + 1
            lbl = QLabel(name)
            lbl.setStyleSheet("font-size: 11pt;")
            grid.addWidget(lbl, row, 0)

            key1 = s.value(f"{setting_key}_1", default1)
            key2 = s.value(f"{setting_key}_2", default2)

            edit1 = KeyCaptureEdit(key1)
            edit1.setFixedWidth(180)
            grid.addWidget(edit1, row, 1)

            edit2 = KeyCaptureEdit(key2)
            edit2.setFixedWidth(180)
            grid.addWidget(edit2, row, 2)

            edits.append((setting_key, edit1, edit2))

        layout.addLayout(grid)
        layout.addWidget(QLabel(""))

        note = QLabel("Ctrl+Wheel always works for zoom. Changes apply after restart.")
        note.setStyleSheet("color: #808080; font-style: italic;")
        layout.addWidget(note)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close
        )

        def save_shortcuts():
            for setting_key, edit1, edit2 in edits:
                s.setValue(f"{setting_key}_1", edit1.text().strip())
                s.setValue(f"{setting_key}_2", edit2.text().strip())
            QMessageBox.information(dlg, "Saved", "Shortcuts saved. Restart Object Explorer to apply.")

        btn_box.button(QDialogButtonBox.StandardButton.Save).clicked.connect(save_shortcuts)
        btn_box.rejected.connect(dlg.close)
        layout.addWidget(btn_box)

        dlg.exec()

    def event(self, event):
        """Handle mouse button 4/5 for back/forward."""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseButtonPress:
            from PySide6.QtGui import QMouseEvent
            if isinstance(event, QMouseEvent):
                if event.button() == Qt.MouseButton.BackButton:
                    self._go_back()
                    return True
                elif event.button() == Qt.MouseButton.ForwardButton:
                    self._go_forward()
                    return True
        return super().event(event)

    def keyPressEvent(self, event):
        """Handle zoom shortcuts directly as fallback."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            key = event.key()
            if key in (Qt.Key.Key_Equal, Qt.Key.Key_Plus):
                self._zoom_in()
                return
            elif key == Qt.Key.Key_Minus:
                self._zoom_out()
                return
            elif key == Qt.Key.Key_0:
                self._zoom_reset()
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """Handle Ctrl+wheel for zoom."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def _show_object_details(self, path: str):
        """Show properties and references for an object path."""
        # Load object from DB
        obj = self.db.get_object(path) if self.db else None

        # Try loading JSON property data
        json_data = self._load_json_for_path(path)

        # Properties tab
        if json_data:
            data = json_data.get("_data", {})
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.prop_view.setPlainText(formatted)
        elif obj and obj.get("properties"):
            formatted = json.dumps(obj["properties"], indent=2, ensure_ascii=False)
            self.prop_view.setPlainText(formatted)
        else:
            class_name = obj.get("class_name", "") if obj else ""
            lines = [f"Path: {path}"]
            if class_name:
                lines.insert(0, f"Class: {class_name}")
            if not self._json_data_dir:
                lines.append("")
                lines.append("(No property data — set a JSON data directory via 'Load Datapack')")
                lines.append("")
                lines.append("To get property data, download Grimm's serialized files from:")
                lines.append("https://www.nexusmods.com/borderlands3/mods/247")
                lines.append("Then click 'Load Datapack' → 'Set JSON Data Directory'")
            else:
                lines.append("")
                lines.append("(No JSON file found for this object)")
            self.prop_view.setPlainText("\n".join(lines))

        # References tab — check main db AND separate refs db, combine results
        self.refs_from.clear()
        refs_from = set()
        if self.db:
            refs_from.update(self.db.get_references_from(path))
        if self._refs_db:
            refs_from.update(self._refs_db.get_references_from(path))
        for ref in sorted(refs_from):
            ref_item = QTreeWidgetItem()
            ref_item.setText(0, ref)
            ref_item.setData(0, Qt.ItemDataRole.UserRole, ref)
            self.refs_from.addTopLevelItem(ref_item)

        self.refs_to.clear()
        refs_to = set()
        if self.db:
            refs_to.update(self.db.get_references_to(path))
        if self._refs_db:
            refs_to.update(self._refs_db.get_references_to(path))
        for ref in sorted(refs_to):
            ref_item = QTreeWidgetItem()
            ref_item.setText(0, ref)
            ref_item.setData(0, Qt.ItemDataRole.UserRole, ref)
            self.refs_to.addTopLevelItem(ref_item)

    # ── Search ──

    def _on_search_text_changed(self):
        """Debounce search input."""
        # Longer debounce for property search since it's expensive
        if self.search_props_cb.isChecked():
            self._search_timer.setInterval(800)
        else:
            self._search_timer.setInterval(300)
        self._search_timer.start()

    def _do_search(self):
        """Execute the search."""
        if not self.db:
            return

        query = self.search_box.text().strip()
        if not query:
            self._populate_root()
            return

        selected_class = self.search_class.currentText()
        search_props = self.search_props_cb.isChecked()

        if search_props:
            self.status_label.setText(f"Searching properties for '{query}'...")
            self.tree.clear()
            QApplication.processEvents()

            # Run in chunks to keep UI responsive
            results = []
            query_lower = query.lower()
            if self.db.has_objects:
                import zlib
                cursor = self.db.conn.execute(
                    "SELECT path, class_name, data FROM objects WHERE data IS NOT NULL"
                )
                batch_count = 0
                for row in cursor:
                    if len(results) >= 200:
                        break
                    raw = row["data"]
                    try:
                        if isinstance(raw, bytes):
                            try:
                                text = zlib.decompress(raw).decode("utf-8", errors="replace")
                            except zlib.error:
                                text = raw.decode("utf-8", errors="replace")
                        elif isinstance(raw, str):
                            text = raw
                        else:
                            continue
                        if query_lower in text.lower():
                            results.append({
                                "path": row["path"],
                                "class_name": row["class_name"] or "",
                            })
                    except Exception:
                        continue

                    batch_count += 1
                    if batch_count % 5000 == 0:
                        self.status_label.setText(
                            f"Searching properties for '{query}'... ({batch_count:,} scanned, {len(results)} found)"
                        )
                        QApplication.processEvents()
        elif selected_class != "All Classes":
            results = self.db.search_by_class(selected_class)
            results = [r for r in results if query.lower() in r["path"].lower()]
        else:
            results = self.db.search_objects(query)

        self.tree.clear()
        for r in results:
            item = QTreeWidgetItem()
            item.setText(0, r["path"])
            item.setText(1, r.get("class_name", ""))
            item.setData(0, Qt.ItemDataRole.UserRole, r["path"])
            item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
            self.tree.addTopLevelItem(item)

        self.status_label.setText(f"Search: {len(results)} results for '{query}'" +
                                  (" (in properties)" if search_props else ""))

    # ── Context menu ──

    def _tree_context_menu(self, pos):
        """Right-click context menu on tree items."""
        from PySide6.QtWidgets import QMenu
        item = self.tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        path = item.data(0, Qt.ItemDataRole.UserRole)

        if path:
            menu.addAction("Copy Path", lambda: self._copy_text(path))
            menu.addAction("Copy as 'set' command", lambda: self._copy_text(f"set {path} "))
            menu.addAction("Copy as 'edit' command", lambda: self._copy_text(f"edit {path} "))
            menu.addSeparator()
            menu.addAction("Show References", lambda: self._navigate_to(path))

        menu.exec(self.tree.mapToGlobal(pos))

    # ── Clipboard ──

    def _copy_path(self):
        """Copy the current object path to clipboard."""
        path = self.path_label.text()
        if path:
            QApplication.clipboard().setText(path)

    def _copy_as_entry(self):
        """Copy a ready-to-use set command template."""
        path = self.path_label.text()
        if path:
            QApplication.clipboard().setText(f"set {path} ")

    def _copy_text(self, text: str):
        QApplication.clipboard().setText(text)

    # ── Find dialog ──

    def _show_find_dialog(self):
        """Show a floating find dialog for the properties panel."""
        if self._find_dialog and self._find_dialog.isVisible():
            self._find_dialog.raise_()
            self._find_dialog._edit.setFocus()
            self._find_dialog._edit.selectAll()
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Search")
        dlg.setMinimumWidth(700)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.Tool)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        lbl = QLabel("Search For:")
        lbl.setStyleSheet("font-size: 12pt;")
        search_row.addWidget(lbl)
        edit = QLineEdit()
        edit.setMinimumHeight(32)
        edit.setStyleSheet("font-size: 12pt;")
        search_row.addWidget(edit, stretch=1)
        btn_prev = QPushButton("Prev")
        btn_prev.setMinimumWidth(70)
        btn_prev.setMinimumHeight(32)
        search_row.addWidget(btn_prev)
        btn_next = QPushButton("Next")
        btn_next.setMinimumWidth(70)
        btn_next.setMinimumHeight(32)
        search_row.addWidget(btn_next)
        layout.addLayout(search_row)

        # Options
        from PySide6.QtWidgets import QCheckBox
        cb_regex = QCheckBox("Regular expression")
        cb_regex.setStyleSheet("font-size: 11pt;")
        cb_case = QCheckBox("Match case")
        cb_case.setStyleSheet("font-size: 11pt;")
        cb_wrap = QCheckBox("Wrap around")
        cb_wrap.setStyleSheet("font-size: 11pt;")
        cb_wrap.setChecked(True)
        layout.addWidget(cb_regex)
        layout.addWidget(cb_case)
        layout.addWidget(cb_wrap)

        # Cancel button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumWidth(90)
        btn_cancel.setMinimumHeight(32)
        btn_cancel.clicked.connect(dlg.close)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        def _get_active_view():
            """Get the QTextBrowser for the currently focused property tab."""
            parent = self.parent()
            if parent and hasattr(parent, 'prop_tabs'):
                widget = parent.prop_tabs.currentWidget()
                if hasattr(widget, '_browser'):
                    return widget._browser
                if isinstance(widget, (QTextEdit, QTextBrowser)):
                    return widget
            return self.prop_view

        def _build_flags():
            from PySide6.QtGui import QTextDocument
            flags = QTextDocument.FindFlag(0)
            if cb_case.isChecked():
                flags |= QTextDocument.FindFlag.FindCaseSensitively
            return flags

        def find_next():
            text = edit.text()
            if not text:
                return
            view = _get_active_view()
            flags = _build_flags()
            if cb_regex.isChecked():
                from PySide6.QtCore import QRegularExpression as QRE
                regex = QRE(text)
                if not cb_case.isChecked():
                    regex.setPatternOptions(QRE.PatternOption.CaseInsensitiveOption)
                found = view.find(regex, flags)
            else:
                found = view.find(text, flags)
            if not found and cb_wrap.isChecked():
                cursor = view.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                view.setTextCursor(cursor)
                if cb_regex.isChecked():
                    view.find(regex, flags)
                else:
                    view.find(text, flags)

        def find_prev():
            from PySide6.QtGui import QTextDocument
            text = edit.text()
            if not text:
                return
            view = _get_active_view()
            flags = _build_flags() | QTextDocument.FindFlag.FindBackward
            if cb_regex.isChecked():
                from PySide6.QtCore import QRegularExpression as QRE
                regex = QRE(text)
                if not cb_case.isChecked():
                    regex.setPatternOptions(QRE.PatternOption.CaseInsensitiveOption)
                found = view.find(regex, flags)
            else:
                found = view.find(text, flags)
            if not found and cb_wrap.isChecked():
                cursor = view.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                view.setTextCursor(cursor)
                if cb_regex.isChecked():
                    view.find(regex, flags)
                else:
                    view.find(text, flags)

        edit.returnPressed.connect(find_next)
        btn_next.clicked.connect(find_next)
        btn_prev.clicked.connect(find_prev)

        dlg._edit = edit
        self._find_dialog = dlg
        dlg.show()
        edit.setFocus()


class ObjectExplorerDialog(QWidget):
    """Standalone Object Explorer window with tabbed properties and clickable links."""

    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowTitle("Object Explorer \u2014 OpenBL3CMM")
        self.resize(1200, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.explorer = ObjectExplorerWidget(self)
        layout.addWidget(self.explorer)

        self._setup_tabbed_properties()
        self.explorer.tree.viewport().installEventFilter(self)

    def _setup_tabbed_properties(self):
        exp = self.explorer

        self.prop_tabs = QTabWidget()
        self.prop_tabs.setTabsClosable(True)
        self.prop_tabs.setMovable(True)
        self.prop_tabs.tabCloseRequested.connect(self._close_prop_tab)
        self.prop_tabs.tabBarClicked.connect(self._on_tab_clicked)

        # Move original prop_view into first tab wrapped in container
        exp.tabs.removeTab(0)
        first_container = self._make_container_for_existing(exp.prop_view)
        self.prop_tabs.addTab(first_container, "Properties")

        # "+" tab always last
        self._plus_widget = QWidget()
        self._plus_idx = self.prop_tabs.addTab(self._plus_widget, "+")
        self.prop_tabs.tabBar().setTabButton(
            self._plus_idx, self.prop_tabs.tabBar().ButtonPosition.RightSide, None
        )

        exp.tabs.insertTab(0, self.prop_tabs, "Properties")
        exp.tabs.setCurrentIndex(0)

        exp.prop_view.viewport().installEventFilter(self)

        # Patch _show_object_details to linkify and update active tab
        self._original_show = exp._show_object_details
        exp._show_object_details = self._patched_show_details

    def _patched_show_details(self, path):
        """Patched version that linkifies paths and updates the active tab."""
        cur_idx = self.prop_tabs.currentIndex()
        cur_widget = self.prop_tabs.widget(cur_idx)

        if cur_idx == self._plus_idx:
            return

        # Load into whatever tab is active (including the first/main one)
        self._load_into_view(cur_widget, path)

        short_name = path.rsplit("/", 1)[-1] if "/" in path else path
        if cur_idx >= 0:
            self.prop_tabs.setTabText(cur_idx, short_name)

    def _load_into_view(self, widget, path):
        """Load object data into a specific view (QTextBrowser or container)."""
        view = self._get_browser(widget)
        if not view:
            return
        exp = self.explorer
        obj = exp.db.get_object(path) if exp.db else None
        json_data = exp._load_json_for_path(path)

        if json_data:
            data = json_data.get("_data", {})
            plain = json.dumps(data, indent=2, ensure_ascii=False)
        elif obj and obj.get("properties"):
            plain = json.dumps(obj["properties"], indent=2, ensure_ascii=False)
        else:
            plain = f"Path: {path}\n\n(No property data available)"

        html = self._linkify_paths(plain)
        view.setHtml(html)
        view.moveCursor(view.textCursor().MoveOperation.Start)

        if hasattr(widget, '_current_path'):
            widget._current_path = path

        # Update references panel
        exp.refs_from.clear()
        exp.refs_to.clear()
        if exp.db:
            refs_from = set(exp.db.get_references_from(path))
            refs_to = set(exp.db.get_references_to(path))
            if exp._refs_db:
                refs_from.update(exp._refs_db.get_references_from(path))
                refs_to.update(exp._refs_db.get_references_to(path))
            for ref in sorted(refs_from):
                ref_item = QTreeWidgetItem()
                ref_item.setText(0, ref)
                ref_item.setData(0, Qt.ItemDataRole.UserRole, ref)
                exp.refs_from.addTopLevelItem(ref_item)
            for ref in sorted(refs_to):
                ref_item = QTreeWidgetItem()
                ref_item.setText(0, ref)
                ref_item.setData(0, Qt.ItemDataRole.UserRole, ref)
                exp.refs_to.addTopLevelItem(ref_item)

    def _on_tab_clicked(self, index):
        if index == self._plus_idx:
            view = self._make_browser()
            new_idx = self.prop_tabs.insertTab(self._plus_idx, view, "New Tab")
            self._plus_idx = self.prop_tabs.count() - 1
            self.prop_tabs.setCurrentIndex(new_idx)

    def _make_container_for_existing(self, existing_browser):
        """Wrap an existing QTextBrowser in a container with clipboard buttons."""
        container = QWidget()
        vlayout = QVBoxLayout(container)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)

        vlayout.addWidget(existing_browser, stretch=1)

        # Clipboard/saved panel
        saved_widget = QWidget()
        saved_layout = QVBoxLayout(saved_widget)
        saved_layout.setContentsMargins(4, 2, 4, 2)
        saved_layout.setSpacing(2)

        saved_header = QHBoxLayout()
        btn_save = QPushButton("Save Current")
        btn_save.setMinimumHeight(26)
        btn_save.setStyleSheet("font-size: 10pt; padding: 2px 8px;")
        btn_save.clicked.connect(lambda: self._save_to_clipboard(container))
        saved_header.addWidget(btn_save)
        btn_toggle = QPushButton("Saved Items")
        btn_toggle.setMinimumHeight(26)
        btn_toggle.setStyleSheet("font-size: 10pt; padding: 2px 8px;")
        btn_toggle.setCheckable(True)
        btn_toggle.setChecked(False)
        saved_header.addWidget(btn_toggle)
        saved_layout.addLayout(saved_header)

        saved_list = QTreeWidget()
        saved_list.setHeaderLabels(["Saved Objects"])
        saved_list.setMaximumHeight(120)
        saved_list.hide()
        saved_list.itemDoubleClicked.connect(
            lambda item, col: self._navigate_in_tab(
                self.prop_tabs.indexOf(container),
                item.data(0, Qt.ItemDataRole.UserRole)
            ) if item.data(0, Qt.ItemDataRole.UserRole) else None
        )
        saved_layout.addWidget(saved_list)
        btn_toggle.toggled.connect(saved_list.setVisible)

        vlayout.addWidget(saved_widget)

        container._browser = existing_browser
        container._saved_list = saved_list
        container._current_path = ""

        return container

    def _make_browser(self):
        """Create a new tab widget with browser + clipboard."""
        container = QWidget()
        vlayout = QVBoxLayout(container)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)

        browser = QTextBrowser()
        fs = self.explorer._prop_font_size
        browser.setFont(QFont("Consolas", fs))
        browser.setStyleSheet(f"font-family: Consolas, monospace; font-size: {fs}pt;")
        browser.setReadOnly(True)
        browser.setOpenLinks(False)
        browser.setOpenExternalLinks(False)
        browser.viewport().installEventFilter(self)
        vlayout.addWidget(browser, stretch=1)

        # Clipboard/saved panel (collapsed by default)
        saved_widget = QWidget()
        saved_layout = QVBoxLayout(saved_widget)
        saved_layout.setContentsMargins(4, 2, 4, 2)
        saved_layout.setSpacing(2)

        saved_header = QHBoxLayout()
        btn_save = QPushButton("Save Current")
        btn_save.setMinimumHeight(26)
        btn_save.setStyleSheet("font-size: 10pt; padding: 2px 8px;")
        btn_save.clicked.connect(lambda: self._save_to_clipboard(container))
        saved_header.addWidget(btn_save)
        btn_toggle = QPushButton("Saved Items")
        btn_toggle.setMinimumHeight(26)
        btn_toggle.setStyleSheet("font-size: 10pt; padding: 2px 8px;")
        btn_toggle.setCheckable(True)
        btn_toggle.setChecked(False)
        saved_header.addWidget(btn_toggle)
        saved_layout.addLayout(saved_header)

        saved_list = QTreeWidget()
        saved_list.setHeaderLabels(["Saved Objects"])
        saved_list.setMaximumHeight(120)
        saved_list.hide()
        saved_list.itemDoubleClicked.connect(
            lambda item, col: self._navigate_in_tab(
                self.prop_tabs.indexOf(container),
                item.data(0, Qt.ItemDataRole.UserRole)
            ) if item.data(0, Qt.ItemDataRole.UserRole) else None
        )
        saved_layout.addWidget(saved_list)
        btn_toggle.toggled.connect(saved_list.setVisible)

        vlayout.addWidget(saved_widget)

        # Store refs on the container for later access
        container._browser = browser
        container._saved_list = saved_list
        container._current_path = ""

        return container

    def _save_to_clipboard(self, container):
        """Save the current object path to this tab's clipboard."""
        path = self.explorer.path_label.text()
        if not path:
            return
        saved_list = container._saved_list
        # Don't add duplicates
        for i in range(saved_list.topLevelItemCount()):
            if saved_list.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == path:
                return
        item = QTreeWidgetItem()
        short_name = path.rsplit("/", 1)[-1] if "/" in path else path
        item.setText(0, short_name)
        item.setToolTip(0, path)
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        saved_list.addTopLevelItem(item)

    def _get_browser(self, widget):
        """Get the QTextBrowser from a tab widget (handles both raw browser and container)."""
        if isinstance(widget, QTextBrowser):
            return widget
        if hasattr(widget, '_browser'):
            return widget._browser
        return None

    def _linkify_paths(self, text):
        import html as html_mod
        import re
        escaped = html_mod.escape(text)
        # Match object paths inside quotes - only /Game/, /Engine/, DLC paths
        pattern = r'(&quot;)(\/(?:Game|Engine|Alisma|Dandelion|Geranium|Hibiscus|Ixora|Ixora2)\/[A-Za-z0-9_/.\-:]+)(&quot;)'
        def replace_path(m):
            pre, path, post = m.group(1), m.group(2), m.group(3)
            return f'{pre}<a href="obj:{path}" style="color: #6eaaff; text-decoration: none;">{path}</a>{post}'
        linked = re.sub(pattern, replace_path, escaped)
        fs = self.explorer._prop_font_size
        return (
            f'<pre style="font-family: Consolas, monospace; font-size: {fs}pt; '
            f'color: #d4d4d4; white-space: pre-wrap;">{linked}</pre>'
        )

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent, QWheelEvent

        # Ctrl+Wheel zoom
        if event.type() == QEvent.Type.Wheel and isinstance(event, QWheelEvent):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.explorer._zoom_in()
                else:
                    self.explorer._zoom_out()
                return True

        if not isinstance(event, QMouseEvent):
            return super().eventFilter(obj, event)

        # Mouse 4/5 back/forward
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.BackButton:
                self.explorer._go_back()
                return True
            if event.button() == Qt.MouseButton.ForwardButton:
                self.explorer._go_forward()
                return True

        # Middle-click on tree -> new tab
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.MiddleButton:
                if obj is self.explorer.tree.viewport():
                    item = self.explorer.tree.itemAt(event.position().toPoint())
                    if item:
                        path = item.data(0, Qt.ItemDataRole.UserRole)
                        is_folder = item.data(0, Qt.ItemDataRole.UserRole + 1)
                        if path and not is_folder:
                            self._open_in_new_tab(path)
                            return True

        # Left/middle click on links in ANY tab
        if event.type() == QEvent.Type.MouseButtonRelease:
            for i in range(self.prop_tabs.count()):
                widget = self.prop_tabs.widget(i)
                browser = self._get_browser(widget)
                if browser and obj is browser.viewport():
                    anchor = browser.anchorAt(event.position().toPoint())
                    if anchor and anchor.startswith("obj:"):
                        obj_path = anchor[4:]
                        if event.button() == Qt.MouseButton.MiddleButton:
                            self._open_in_new_tab(obj_path)
                        elif event.button() == Qt.MouseButton.LeftButton:
                            self._navigate_in_tab(i, obj_path)
                        return True
                # Also check if it's the raw prop_view (first tab, no container)
                if isinstance(widget, QTextBrowser) and obj is widget.viewport():
                    anchor = widget.anchorAt(event.position().toPoint())
                    if anchor and anchor.startswith("obj:"):
                        obj_path = anchor[4:]
                        if event.button() == Qt.MouseButton.MiddleButton:
                            self._open_in_new_tab(obj_path)
                        elif event.button() == Qt.MouseButton.LeftButton:
                            self._navigate_in_tab(i, obj_path)
                        return True

        return super().eventFilter(obj, event)

    def _navigate_in_tab(self, tab_idx, path):
        """Navigate to an object within a specific tab."""
        self.explorer.path_label.setText(path)

        # Add to history
        if not self.explorer._navigating_history:
            if self.explorer._history_idx < len(self.explorer._history) - 1:
                self.explorer._history = self.explorer._history[:self.explorer._history_idx + 1]
            self.explorer._history.append(path)
            self.explorer._history_idx = len(self.explorer._history) - 1
            self.explorer._update_nav_buttons()

        widget = self.prop_tabs.widget(tab_idx)
        self._load_into_view(widget, path)
        short_name = path.rsplit("/", 1)[-1] if "/" in path else path
        self.prop_tabs.setTabText(tab_idx, short_name)

        # Also update references
        if self.explorer.db:
            self.explorer.refs_from.clear()
            self.explorer.refs_to.clear()
            refs_from = set()
            refs_to = set()
            refs_from.update(self.explorer.db.get_references_from(path))
            refs_to.update(self.explorer.db.get_references_to(path))
            if self.explorer._refs_db:
                refs_from.update(self.explorer._refs_db.get_references_from(path))
                refs_to.update(self.explorer._refs_db.get_references_to(path))
            for ref in sorted(refs_from):
                ref_item = QTreeWidgetItem()
                ref_item.setText(0, ref)
                ref_item.setData(0, Qt.ItemDataRole.UserRole, ref)
                self.explorer.refs_from.addTopLevelItem(ref_item)
            for ref in sorted(refs_to):
                ref_item = QTreeWidgetItem()
                ref_item.setText(0, ref)
                ref_item.setData(0, Qt.ItemDataRole.UserRole, ref)
                self.explorer.refs_to.addTopLevelItem(ref_item)

    def _open_in_new_tab(self, path):
        view = self._make_browser()
        self._load_into_view(view, path)
        short_name = path.rsplit("/", 1)[-1] if "/" in path else path
        idx = self.prop_tabs.insertTab(self._plus_idx, view, short_name)
        self._plus_idx = self.prop_tabs.count() - 1
        self.prop_tabs.setCurrentIndex(idx)

    def _close_prop_tab(self, index):
        if index == self._plus_idx:
            return
        real_count = self.prop_tabs.count() - 1
        if real_count <= 1:
            return
        w = self.prop_tabs.widget(index)
        if w is self.explorer.prop_view:
            return
        # Switch to previous tab before removing
        if index > 0:
            self.prop_tabs.setCurrentIndex(index - 1)
        self.prop_tabs.removeTab(index)
        self._plus_idx = self.prop_tabs.count() - 1
        if w:
            w.deleteLater()