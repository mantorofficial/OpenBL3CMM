"""
Hotfix syntax highlighter and validator for OpenBL3CMM.

Provides:
  - HotfixHighlighter: QSyntaxHighlighter that colors command parts in real-time
  - validate_hotfix(): checks for problems before saving, returns list of issues

Colors:
  - Command name (set, edit, etc.) → green if valid, red if not
  - Object path (/Game/...) → green if found in datapack, orange if not
  - Property/attribute → green if found in object's JSON, default otherwise
  - Value → default color (white/light)
"""
from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextDocument,
)

# Known simple commands
VALID_COMMANDS = {
    "set", "set_cmp", "clone", "delete", "create", "set_array",
    "add", "remove", "set_if", "set_struct", "edit", "early_set",
    "news", "exec", "rename", "merge",
}

# Known Spark types
VALID_SPARK_TYPES = {
    "SparkPatchEntry", "SparkLevelPatchEntry",
    "SparkCharacterLoadedEntry", "SparkEarlyLevelPatchEntry",
    "InjectNewsItem",
}

# Module-level datapack reference — set by MainWindow when OE is loaded
_datapack_db = None


def set_datapack(db):
    """Set the global datapack database for validation."""
    global _datapack_db
    _datapack_db = db


def get_datapack():
    """Get the current datapack database."""
    return _datapack_db


def path_exists(path: str) -> bool:
    """Check if an object path exists in the datapack."""
    db = _datapack_db
    if not db:
        return False
    obj = db.get_object(path)
    return obj is not None


def find_property_in_object(obj_path: str, prop_name: str) -> bool:
    """Check if a property name exists in an object's data."""
    db = _datapack_db
    if not db:
        return False
    obj = db.get_object(obj_path)
    if not obj:
        return False
    props = obj.get("properties", {})
    if not props:
        return False
    # Search recursively in the JSON
    return _find_key_in_dict(props, prop_name)


def _find_key_in_dict(d, key: str) -> bool:
    """Recursively search for a key in nested dicts/lists."""
    key_lower = key.lower()
    if isinstance(d, dict):
        for k, v in d.items():
            if k.lower() == key_lower:
                return True
            if isinstance(v, (dict, list)):
                if _find_key_in_dict(v, key):
                    return True
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, (dict, list)):
                if _find_key_in_dict(item, key):
                    return True
    return False


class HotfixHighlighter(QSyntaxHighlighter):
    """Real-time syntax highlighter for hotfix commands."""

    def __init__(self, parent: QTextDocument):
        super().__init__(parent)

        # Formats
        self.fmt_command_ok = QTextCharFormat()
        self.fmt_command_ok.setForeground(QColor("#4ec954"))  # green
        self.fmt_command_ok.setFontWeight(QFont.Weight.Bold)

        self.fmt_command_bad = QTextCharFormat()
        self.fmt_command_bad.setForeground(QColor("#e05555"))  # red
        self.fmt_command_bad.setFontWeight(QFont.Weight.Bold)

        self.fmt_path_ok = QTextCharFormat()
        self.fmt_path_ok.setForeground(QColor("#4ec954"))  # green

        self.fmt_path_unknown = QTextCharFormat()
        self.fmt_path_unknown.setForeground(QColor("#e8a838"))  # orange

        self.fmt_property_ok = QTextCharFormat()
        self.fmt_property_ok.setForeground(QColor("#4ec954"))  # green

        self.fmt_property = QTextCharFormat()
        self.fmt_property.setForeground(QColor("#80b0e0"))  # blue-ish

        self.fmt_value = QTextCharFormat()
        self.fmt_value.setForeground(QColor("#d4d4d4"))  # light grey

        self.fmt_params = QTextCharFormat()
        self.fmt_params.setForeground(QColor("#888888"))  # dim

    def highlightBlock(self, text: str):
        """Called by Qt for each line of text."""
        stripped = text.strip()
        if not stripped:
            return

        # Check if it's a simple command or Spark format
        if stripped.startswith(("Spark", "Inject")):
            self._highlight_spark(text, stripped)
        else:
            self._highlight_simple(text, stripped)

    def _highlight_simple(self, text: str, stripped: str):
        """Highlight a simple command like: set /Game/Path Prop Value"""
        # Find the command word
        parts = stripped.split(None, 1)
        if not parts:
            return

        cmd = parts[0].lower()
        cmd_start = text.index(parts[0])

        # Color command name
        if cmd in VALID_COMMANDS:
            self.setFormat(cmd_start, len(parts[0]), self.fmt_command_ok)
        else:
            self.setFormat(cmd_start, len(parts[0]), self.fmt_command_bad)

        if len(parts) < 2:
            return

        rest = parts[1]
        rest_start = cmd_start + len(parts[0]) + 1

        # Check for optional params override (...)
        if rest.startswith("("):
            close = rest.find(")")
            if close >= 0:
                self.setFormat(rest_start, close + 1, self.fmt_params)
                rest = rest[close + 1:].lstrip()
                rest_start = text.index(rest, rest_start) if rest and rest in text[rest_start:] else rest_start + close + 2

        if not rest:
            return

        # Split remaining: object path, property, [dtkey, index,] value
        args = rest.split()
        if not args:
            return

        # Object path
        obj_path = args[0]
        obj_start = text.find(obj_path, rest_start)
        if obj_start >= 0:
            if _datapack_db and obj_path.startswith("/"):
                if path_exists(obj_path):
                    self.setFormat(obj_start, len(obj_path), self.fmt_path_ok)
                else:
                    self.setFormat(obj_start, len(obj_path), self.fmt_path_unknown)
            elif obj_path.startswith("/"):
                self.setFormat(obj_start, len(obj_path), self.fmt_path_unknown)

        # Property name
        if len(args) >= 2:
            prop = args[1]
            prop_start = text.find(prop, obj_start + len(obj_path))
            if prop_start >= 0:
                if _datapack_db and obj_path.startswith("/"):
                    if find_property_in_object(obj_path, prop):
                        self.setFormat(prop_start, len(prop), self.fmt_property_ok)
                    else:
                        self.setFormat(prop_start, len(prop), self.fmt_property)
                else:
                    self.setFormat(prop_start, len(prop), self.fmt_property)

        # Value (last arg or everything after property)
        if len(args) >= 3:
            # Color remaining as value
            last_start = text.find(args[2], prop_start + len(args[1]) if len(args) >= 2 else rest_start)
            if last_start >= 0:
                self.setFormat(last_start, len(text) - last_start, self.fmt_value)

    def _highlight_spark(self, text: str, stripped: str):
        """Highlight Spark format: SparkPatchEntry,(1,1,0,),/Game/Path,..."""
        # Split on comma but respect the params parens
        m = re.match(r'(\w+),(\([^)]*\)),(.+)', stripped)
        if not m:
            # Try InjectNewsItem or simpler format
            parts = stripped.split(",", 1)
            if parts:
                spark_type = parts[0].strip()
                start = text.index(spark_type)
                if spark_type in VALID_SPARK_TYPES:
                    self.setFormat(start, len(spark_type), self.fmt_command_ok)
                else:
                    self.setFormat(start, len(spark_type), self.fmt_command_bad)
            return

        spark_type = m.group(1)
        params = m.group(2)
        rest = m.group(3)

        # Type
        type_start = text.index(spark_type)
        if spark_type in VALID_SPARK_TYPES:
            self.setFormat(type_start, len(spark_type), self.fmt_command_ok)
        else:
            self.setFormat(type_start, len(spark_type), self.fmt_command_bad)

        # Params
        params_start = text.index(params, type_start)
        self.setFormat(params_start, len(params), self.fmt_params)

        # Object path, attribute, dtkey, index, _, value
        fields = rest.split(",")
        if fields:
            obj_path = fields[0].strip()
            field_start = text.index(obj_path, params_start + len(params)) if obj_path else -1
            if field_start >= 0 and obj_path.startswith("/"):
                if _datapack_db and path_exists(obj_path):
                    self.setFormat(field_start, len(obj_path), self.fmt_path_ok)
                else:
                    self.setFormat(field_start, len(obj_path), self.fmt_path_unknown)

        if len(fields) >= 2:
            prop = fields[1].strip()
            if prop:
                prop_start = text.find(prop, field_start + len(fields[0]) if field_start >= 0 else 0)
                if prop_start >= 0:
                    if _datapack_db and obj_path and find_property_in_object(obj_path, prop):
                        self.setFormat(prop_start, len(prop), self.fmt_property_ok)
                    else:
                        self.setFormat(prop_start, len(prop), self.fmt_property)


def validate_hotfix(text: str) -> list[str]:
    """
    Validate a hotfix command and return a list of problems.
    Returns empty list if everything looks good.
    """
    problems = []
    stripped = text.strip()

    if not stripped:
        problems.append("Empty command")
        return problems

    # Check if it's Spark format
    if stripped.startswith(("Spark", "Inject")):
        return _validate_spark(stripped)
    else:
        return _validate_simple(stripped)


def _validate_simple(text: str) -> list[str]:
    """Validate a simple command."""
    problems = []
    parts = text.split(None, 1)
    if not parts:
        problems.append("Empty command")
        return problems

    cmd = parts[0].lower()
    if cmd not in VALID_COMMANDS:
        problems.append(f"Unknown command: '{parts[0]}'")

    if len(parts) < 2 or not parts[1].strip():
        problems.append("Missing arguments after command")
        return problems

    rest = parts[1].strip()

    # Skip params if present
    if rest.startswith("("):
        close = rest.find(")")
        if close < 0:
            problems.append("Unclosed params parenthesis")
            return problems
        rest = rest[close + 1:].strip()

    args = rest.split()
    if not args:
        problems.append("Missing object path")
        return problems

    obj_path = args[0]
    # Short-form paths (without /) are valid — game resolves them

    # Command-specific validation
    if cmd in ("set", "set_cmp", "set_array", "set_struct", "set_if"):
        if len(args) < 2:
            problems.append("Missing property name")
        if len(args) < 3:
            problems.append("Missing value")
    elif cmd in ("edit", "early_set"):
        if len(args) < 2:
            problems.append("Missing property name")
    elif cmd in ("clone", "delete"):
        pass  # Just need object path
    elif cmd == "news":
        if len(args) < 1:
            problems.append("Missing news text")
    elif cmd == "add" or cmd == "remove":
        if len(args) < 2:
            problems.append("Missing property name")
        if len(args) < 3:
            problems.append("Missing value")

    # Check against datapack
    if _datapack_db and obj_path.startswith("/"):
        if not path_exists(obj_path):
            problems.append(f"Object path not found in datapack: {obj_path}")

    return problems


def _validate_spark(text: str) -> list[str]:
    """Validate Spark format."""
    problems = []

    if text.startswith("InjectNewsItem"):
        parts = text.split(",", 1)
        if len(parts) < 2 or not parts[1].strip():
            problems.append("Missing news item content")
        return problems

    # Parse: Type,(params),object,attribute,dtkey,index,,value
    m = re.match(r'(\w+),(\([^)]*\)),(.+)', text)
    if not m:
        problems.append("Invalid Spark format — expected: Type,(params),object,attribute,...")
        return problems

    spark_type = m.group(1)
    if spark_type not in VALID_SPARK_TYPES:
        problems.append(f"Unknown Spark type: '{spark_type}'")

    fields = m.group(3).split(",")
    # fields: object, attribute, dtkey, index, (empty), value

    if not fields or not fields[0].strip():
        problems.append("Missing object path")
    else:
        obj_path = fields[0].strip()
        if obj_path.startswith("/") and _datapack_db and not path_exists(obj_path):
            problems.append(f"Object path not found in datapack: {obj_path}")

    if len(fields) < 2 or not fields[1].strip():
        problems.append("Missing attribute/property name")

    # Value should be present (after the empty field)
    if len(fields) >= 6:
        value = fields[-1].strip() if fields[-1].strip() else None
        if not value:
            problems.append("Missing value")

    return problems