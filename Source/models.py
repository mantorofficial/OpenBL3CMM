"""
Data models for OpenBLCMM-BL3.
Represents the tree structure of a BL3 hotfix mod file.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class HotfixType(enum.Enum):
    """Known BL3 hotfix entry types."""
    SparkPatchEntry = "SparkPatchEntry"
    SparkLevelPatchEntry = "SparkLevelPatchEntry"
    SparkCharacterLoadedEntry = "SparkCharacterLoadedEntry"
    SparkEarlyLevelPatchEntry = "SparkEarlyLevelPatchEntry"
    InjectNewsItem = "InjectNewsItem"


@dataclass
class HotfixEntry:
    """
    A single hotfix command line.

    raw_line: the original full line, e.g.
        SparkPatchEntry,(1,1,0,),/Game/...,Prop,0,,Value
    comment: the '#' comment line(s) immediately above this entry (description).
    enabled: whether this entry is active.
    """
    raw_line: str
    comment: str = ""
    enabled: bool = True

    # ---- Parsed fields (populated by parse_entry) ----
    hotfix_type: str = ""
    params: str = ""        # the (1,1,0,...) portion
    object_path: str = ""   # /Game/... object path
    attribute: str = ""     # property name
    remainder: str = ""     # everything after attribute
    _original_cmd: str = "" # original simple command name (clone, delete, etc.)

    def __post_init__(self):
        self._parse()

    def _parse(self):
        """Parse the raw hotfix line into components."""
        line = self.raw_line.strip()
        if not line or line.startswith("#"):
            return

        # Find the hotfix type (everything before the first comma)
        comma_idx = line.find(",")
        if comma_idx == -1:
            self.hotfix_type = line
            return

        self.hotfix_type = line[:comma_idx]

        rest = line[comma_idx + 1:]

        # InjectNewsItem has a different format: Header,ImageURL,ArticleURL,Body
        if self.hotfix_type == "InjectNewsItem":
            self.remainder = rest
            return

        # For Spark* entries, the next field is the params in parens: (1,1,0,...)
        # Find the matching closing paren
        if rest.startswith("("):
            paren_depth = 0
            for i, ch in enumerate(rest):
                if ch == "(":
                    paren_depth += 1
                elif ch == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        self.params = rest[:i + 1]
                        rest = rest[i + 1:]
                        if rest.startswith(","):
                            rest = rest[1:]
                        break

        # Now rest should be: object_path,attribute,extra_key,extra_val,,value
        # Split on comma, but be careful — the value field can contain commas
        # The format is: object,attribute,dataTableIndex,dataTableColumn,exportMode,,value
        # We'll grab the object path (first field) and attribute (second field)
        parts = rest.split(",", 2)
        if len(parts) >= 1:
            self.object_path = parts[0]
        if len(parts) >= 2:
            self.attribute = parts[1]
        if len(parts) >= 3:
            self.remainder = parts[2]

    def to_line(self) -> str:
        """Reconstruct the hotfix line from components."""
        return self.raw_line

    @property
    def simple_form(self) -> str:
        """Return the simple command representation, or raw_line if can't convert."""
        try:
            from commands import spark_to_simple
            result = spark_to_simple(self.raw_line)
            if result:
                return result
        except ImportError:
            pass
        return self.raw_line

    @property
    def simple_type(self) -> str:
        """Return the simple command name (set, edit, merge, etc.) or the Spark type."""
        if self._original_cmd:
            return self._original_cmd
        try:
            from commands import spark_to_simple
            result = spark_to_simple(self.raw_line)
            if result:
                return result.split()[0]
        except ImportError:
            pass
        return self.hotfix_type

    @property
    def display_name(self) -> str:
        """Short display name for the tree view — shows the simple command form."""
        return self.simple_form or self.raw_line[:120]


@dataclass
class Category:
    """
    A category (section) in the mod tree.
    Can contain subcategories and/or hotfix entries.
    Mirrors BLCMM's <category> element.
    """
    name: str
    children: list[Category | HotfixEntry] = field(default_factory=list)
    parent: Optional[Category] = field(default=None, repr=False)
    enabled: bool = True
    mutually_exclusive: bool = False  # MUT category

    def add_child(self, child: Category | HotfixEntry):
        if isinstance(child, Category):
            child.parent = self
        self.children.append(child)

    def remove_child(self, child: Category | HotfixEntry):
        self.children.remove(child)
        if isinstance(child, Category):
            child.parent = None

    def entry_count(self, recursive: bool = True) -> int:
        """Count hotfix entries in this category."""
        count = 0
        for child in self.children:
            if isinstance(child, HotfixEntry):
                count += 1
            elif recursive and isinstance(child, Category):
                count += child.entry_count(recursive=True)
        return count

    def enabled_entry_count(self, recursive: bool = True) -> int:
        """Count enabled hotfix entries."""
        count = 0
        for child in self.children:
            if isinstance(child, HotfixEntry) and child.enabled:
                count += 1
            elif recursive and isinstance(child, Category):
                count += child.enabled_entry_count(recursive=True)
        return count


@dataclass
class ModFile:
    """
    Represents an entire .bl3hotfix mod file.
    """
    # Metadata from ### header
    name: str = "Untitled Mod"
    version: str = ""
    author: str = ""
    contact: str = ""
    categories_tag: str = ""
    license_name: str = ""
    license_url: str = ""
    description: str = ""
    extra_header_lines: list[str] = field(default_factory=list)

    # The root category containing all sections
    root: Category = field(default_factory=lambda: Category(name="Root"))

    # Original file path (if loaded from file)
    file_path: str = ""

    def all_entries(self, enabled_only: bool = False) -> list[HotfixEntry]:
        """Recursively collect all hotfix entries."""
        results = []
        self._collect_entries(self.root, results, enabled_only)
        return results

    def _collect_entries(self, cat: Category, out: list, enabled_only: bool):
        for child in cat.children:
            if isinstance(child, HotfixEntry):
                if not enabled_only or child.enabled:
                    out.append(child)
            elif isinstance(child, Category):
                self._collect_entries(child, out, enabled_only)