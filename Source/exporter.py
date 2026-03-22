"""
Exporter for .bl3hotfix files.
Converts a ModFile tree back into the flat text format compatible with OHL/B3HM.
"""
from __future__ import annotations

from pathlib import Path

from models import ModFile, Category, HotfixEntry


def export_to_text(mod: ModFile, enabled_only: bool = False) -> str:
    """Export a ModFile to .bl3hotfix text format."""
    lines: list[str] = []

    # ---- Header (### format) ----
    lines.append("###")
    if mod.name:
        lines.append(f"### Name: {mod.name}")
    if mod.version:
        lines.append(f"### Version: {mod.version}")
    if mod.author:
        lines.append(f"### Author: {mod.author}")
    if mod.contact:
        lines.append(f"### Contact: {mod.contact}")
    if mod.categories_tag:
        lines.append(f"### Categories: {mod.categories_tag}")
    lines.append("###")
    if mod.license_name:
        lines.append(f"### License: {mod.license_name}")
    if mod.license_url:
        lines.append(f"### License URL: {mod.license_url}")
        lines.append("###")

    if mod.description:
        lines.append("")
        for desc_line in mod.description.splitlines():
            if desc_line.strip():
                lines.append(f"### {desc_line}")
            else:
                lines.append("###")
        lines.append("")

    # ---- BLIMP tags (for tools that read them) ----
    try:
        from blimp import BlimpMetadata, generate_blimp_block
        meta = BlimpMetadata(
            title=mod.name,
            version=mod.version,
            description=mod.description,
            license_name=mod.license_name,
            license_url=mod.license_url,
            contact=mod.contact,
            categories=mod.categories_tag,
            games=["BL3"],
        )
        if mod.author:
            meta.authors = [mod.author]
        blimp_block = generate_blimp_block(meta)
        if blimp_block:
            lines.append(blimp_block)
            lines.append("")
    except ImportError:
        pass

    # ---- Body ----
    # Flatten: get the actual content categories, skipping redundant "root" wrappers
    children = _get_exportable_children(mod.root)
    for child in children:
        if isinstance(child, Category):
            _export_category(child, lines, depth=0, enabled_only=enabled_only)

    # Ensure trailing newline
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def _get_exportable_children(root: Category) -> list:
    """Flatten nested 'root' categories to avoid wrapping on each save."""
    children = root.children
    # Keep unwrapping if the only child is a Category named "root"
    while (len(children) == 1
           and isinstance(children[0], Category)
           and children[0].name.lower() == "root"):
        children = children[0].children
    return children


def _export_category(cat: Category, lines: list[str], depth: int, enabled_only: bool):
    """Export a category and its children."""
    if enabled_only and cat.enabled_entry_count() == 0:
        return

    lines.append("")

    if depth == 0:
        # Major section header
        border = "#" * max(len(cat.name) + 16, 30)
        lines.append(border)
        padding = (len(border) - len(cat.name) - 2) // 2
        name_line = "#" * padding + " " + cat.name + " " + "#" * padding
        # Ensure same length as border
        while len(name_line) < len(border):
            name_line += "#"
        lines.append(name_line)
        lines.append(border)
    else:
        # Subsection header
        lines.append(f"### {cat.name} ###")

    lines.append("")

    for child in cat.children:
        if isinstance(child, Category):
            _export_category(child, lines, depth=depth + 1, enabled_only=enabled_only)
        elif isinstance(child, HotfixEntry):
            if enabled_only and not child.enabled:
                continue
            _export_entry(child, lines)


def _export_entry(entry: HotfixEntry, lines: list[str]):
    """Export a single hotfix entry."""
    if entry.comment:
        for comment_line in entry.comment.splitlines():
            lines.append(f"# {comment_line}")

    if entry.enabled:
        lines.append(entry.raw_line)
    else:
        # Disabled entries are commented out so the game skips them
        lines.append(f"#{entry.raw_line}")


def export_to_file(mod: ModFile, path: str | Path, enabled_only: bool = False):
    """Export a ModFile to a .bl3hotfix or .blmod file."""
    path = Path(path)

    # Handle .blmod export
    if path.suffix.lower() == ".blmod":
        try:
            from blmod import export_blmod_file
            export_blmod_file(mod, str(path), enabled_only=enabled_only)
            return
        except ImportError:
            raise ValueError("PyYAML is required for .blmod export. Install with: pip install pyyaml")

    text = export_to_text(mod, enabled_only=enabled_only)
    path.write_text(text, encoding="utf-8")