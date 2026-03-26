"""
.blmod file format (v1) parser and serializer.

The .blmod format is a YAML-based mod file format designed by apple1417
as a replacement for .blcm, applicable to BL3/WL/BL4 hotfix mods.

Structure:
  - Document 1 (header): blmod magic, version, encoding, games, metadata
  - Document 2 (content): nested categories with enabled/disabled commands

Reference: https://gist.github.com/apple1417/b3a02131bc91f0a3267e1cde9d778192

Requires: pip install pyyaml
"""
from __future__ import annotations

from models import ModFile, Category, HotfixEntry

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


BLMOD_VERSION = 1


def can_parse_blmod() -> bool:
    """Check if PyYAML is available for .blmod support."""
    return HAS_YAML


# ──────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────

def parse_blmod_file(path: str) -> ModFile:
    """Parse a .blmod file into a ModFile."""
    if not HAS_YAML:
        raise ImportError("PyYAML is required for .blmod support. Install with: pip install pyyaml")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return parse_blmod_text(content, file_path=path)


def parse_blmod_text(text: str, file_path: str = "") -> ModFile:
    """Parse .blmod text content into a ModFile."""
    if not HAS_YAML:
        raise ImportError("PyYAML is required for .blmod support.")

    docs = list(yaml.safe_load_all(text))

    if len(docs) < 2:
        raise ValueError("Invalid .blmod file: expected two YAML documents (header + content)")

    header = docs[0]
    content = docs[1]

    # Validate header
    if not isinstance(header, dict) or "blmod" not in header:
        raise ValueError("Invalid .blmod file: missing 'blmod' magic in header")

    version = header.get("version", 0)
    if version != BLMOD_VERSION:
        raise ValueError(f"Unsupported .blmod version: {version} (only v{BLMOD_VERSION} supported)")

    # Extract metadata
    metadata = header.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    games = header.get("games", [])
    if not isinstance(games, list):
        games = []

    mod = ModFile(
        name=metadata.get("title", metadata.get("@title", "")),
        version=str(metadata.get("version", metadata.get("@version", ""))),
        author=metadata.get("author", metadata.get("@author", "")),
        description=metadata.get("description", metadata.get("@description", "")),
        contact=metadata.get("contact", ""),
        categories_tag=", ".join(str(g) for g in games),
    )
    mod.file_path = file_path

    # Parse content tree
    if isinstance(content, dict) and "category" in content:
        _parse_category(content, mod.root)
    elif isinstance(content, dict) and "contains" in content:
        # Root category without explicit name
        for item in content.get("contains", []):
            _parse_content_item(item, mod.root)

    return mod


def _parse_category(data: dict, parent: Category):
    """Parse a category dict from .blmod content."""
    name = data.get("category", "Unnamed")
    locked = data.get("locked", False)
    mut = data.get("mut", False)

    cat = Category(name=name, mutually_exclusive=mut)
    parent.add_child(cat)

    pending_comment = ""
    for item in data.get("contains", []):
        if not isinstance(item, dict):
            continue

        if "comment" in item:
            # Collect comment — attach to the next entry
            comment_text = str(item["comment"])
            if pending_comment:
                pending_comment += "\n" + comment_text
            else:
                pending_comment = comment_text
            continue

        if "category" in item:
            _parse_category(item, cat)
            pending_comment = ""

        elif "enabled" in item:
            cmd = item["enabled"]
            if isinstance(cmd, str):
                lines = [l.strip() for l in cmd.strip().splitlines() if l.strip()]
                for j, line in enumerate(lines):
                    comment = pending_comment if j == 0 else ""
                    parent_entry = HotfixEntry(raw_line=line, comment=comment, enabled=True)
                    cat.add_child(parent_entry)
                pending_comment = ""

        elif "disabled" in item:
            cmd = item["disabled"]
            if isinstance(cmd, str):
                cat.add_child(HotfixEntry(raw_line=cmd.strip(), comment=pending_comment, enabled=False))
                pending_comment = ""
            elif isinstance(cmd, list):
                for j, line in enumerate(cmd):
                    if isinstance(line, str) and line.strip():
                        comment = pending_comment if j == 0 else ""
                        cat.add_child(HotfixEntry(raw_line=line.strip(), comment=comment, enabled=False))
                pending_comment = ""


# ──────────────────────────────────────────────
# Serializing
# ──────────────────────────────────────────────

def export_blmod_file(mod: ModFile, path: str, enabled_only: bool = False):
    """Export a ModFile to .blmod format."""
    text = export_blmod_text(mod, enabled_only)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def export_blmod_text(mod: ModFile, enabled_only: bool = False) -> str:
    """
    Export a ModFile to .blmod YAML text.

    Enabled commands use YAML block scalar (|-) so that consumers like OHL
    can read them line-by-line — the command appears on its own line with
    just leading whitespace, which OHL strips before matching.

    Disabled commands use single-line quoted strings so consumers skip them.
    """
    lines = []

    # ── Header document ──
    lines.append("'blmod':")
    lines.append("'version': 1")
    lines.append("'encoding': utf8")
    lines.append("'games':")
    lines.append("  - bl3")

    # Metadata
    meta_lines = []
    if mod.name:
        meta_lines.append(f"  'title': '{_yaml_escape(mod.name)}'")
    if mod.author:
        meta_lines.append(f"  'author': '{_yaml_escape(mod.author)}'")
    if mod.version:
        meta_lines.append(f"  'version': '{_yaml_escape(mod.version)}'")
    if mod.description:
        meta_lines.append(f"  'description': '{_yaml_escape(mod.description)}'")
    if mod.contact:
        meta_lines.append(f"  'contact': '{_yaml_escape(mod.contact)}'")
    if mod.license_name:
        meta_lines.append(f"  'license': '{_yaml_escape(mod.license_name)}'")
    if mod.license_url:
        meta_lines.append(f"  'license-url': '{_yaml_escape(mod.license_url)}'")

    if meta_lines:
        lines.append("'metadata':")
        lines.extend(meta_lines)

    # ── Separator ──
    lines.append("---")

    # ── Content document ──
    _serialize_category_lines(mod.root, lines, indent=0, enabled_only=enabled_only, is_root=True)

    return "\n".join(lines) + "\n"


def _yaml_escape(s: str) -> str:
    """Escape single quotes for YAML single-quoted strings."""
    return s.replace("'", "''")


def _serialize_category_lines(cat: Category, lines: list[str], indent: int,
                               enabled_only: bool, is_root: bool = False):
    """Serialize a category to YAML lines with proper block scalar formatting."""
    prefix = "  " * indent
    name = "root" if is_root else cat.name

    lines.append(f"{prefix}'category': '{_yaml_escape(name)}'")

    if cat.mutually_exclusive:
        lines.append(f"{prefix}'mut': true")

    lines.append(f"{prefix}'contains':")

    for child in cat.children:
        if isinstance(child, Category):
            lines.append(f"{prefix}  - ")  # start list item
            _serialize_category_lines(child, lines, indent + 2, enabled_only)

        elif isinstance(child, HotfixEntry):
            if enabled_only and not child.enabled:
                continue

            if child.comment:
                lines.append(f"{prefix}  - 'comment': '{_yaml_escape(child.comment)}'")

            if child.enabled:
                # Use block scalar (|-) so the command appears on its own
                # indented line — consumers like OHL will see it and strip
                # the leading whitespace before matching
                lines.append(f"{prefix}  - 'enabled': |-")
                lines.append(f"{prefix}      {child.raw_line}")
            else:
                # Disabled: single-line string, consumer won't see it
                lines.append(f"{prefix}  - 'disabled': '{_yaml_escape(child.raw_line)}'")

    # Empty contains
    if not cat.children or (enabled_only and not any(
        isinstance(c, Category) or (isinstance(c, HotfixEntry) and c.enabled)
        for c in cat.children
    )):
        if not any(line.startswith(f"{prefix}  -") for line in lines[-3:]):
            lines.append(f"{prefix}  []")