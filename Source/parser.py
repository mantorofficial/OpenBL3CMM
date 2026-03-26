"""
Parser for .bl3hotfix mod files.
Converts the flat text format into a ModFile tree structure.
"""
from __future__ import annotations

import re
from pathlib import Path

from models import ModFile, Category, HotfixEntry


# Regex patterns for section headers
# Major sections: ##############################
#                 ####### SECTION NAME ########
#                 ##############################
MAJOR_HEADER_RE = re.compile(r"^#{5,}\s*$")
SECTION_NAME_RE = re.compile(r"^#{3,}\s+(.+?)\s+#{3,}$")

# Subsection headers: ### SUBSECTION NAME ###
SUBSECTION_RE = re.compile(r"^###\s+(.+?)\s+###\s*$")

# Metadata lines: ### Key: Value
META_RE = re.compile(r"^###\s+(Name|Version|Author|Contact|Categories|License|License URL):\s*(.*)$", re.IGNORECASE)

# Comment lines
COMMENT_RE = re.compile(r"^#")

# Hotfix entry types
HOTFIX_TYPES = {
    "SparkPatchEntry",
    "SparkLevelPatchEntry",
    "SparkCharacterLoadedEntry",
    "SparkEarlyLevelPatchEntry",
    "InjectNewsItem",
}

# Import simple command support
try:
    from commands import simple_to_spark, SIMPLE_COMMANDS
    _HAS_COMMANDS = True
except ImportError:
    _HAS_COMMANDS = False
    SIMPLE_COMMANDS = []


def is_hotfix_line(line: str) -> bool:
    """Check if a line is a hotfix entry (Spark format or simple command)."""
    stripped = line.strip()
    for ht in HOTFIX_TYPES:
        if stripped.startswith(ht + ",") or stripped == ht:
            return True
    # Also check simple commands
    if _HAS_COMMANDS:
        first_word = stripped.split(None, 1)[0].lower() if stripped else ""
        if first_word in SIMPLE_COMMANDS:
            return True
    return False


def _maybe_convert_simple(line: str) -> str:
    """If line is a simple command, convert to Spark format. Otherwise return as-is."""
    if not _HAS_COMMANDS:
        return line
    stripped = line.strip()
    first_word = stripped.split(None, 1)[0].lower() if stripped else ""
    if first_word in SIMPLE_COMMANDS:
        converted = simple_to_spark(stripped)
        if converted:
            return converted
    return line


def parse_file(path: str | Path) -> ModFile:
    """Parse a mod file (.bl3hotfix, .blmod, .txt) into a ModFile."""
    path = Path(path)

    # Handle .blmod files via the blmod module
    if path.suffix.lower() == ".blmod":
        try:
            from blmod import parse_blmod_file, can_parse_blmod
            if not can_parse_blmod():
                raise ImportError("PyYAML required for .blmod support")
            return parse_blmod_file(str(path))
        except ImportError as e:
            raise ValueError(f"Cannot parse .blmod: {e}")

    text = path.read_text(encoding="utf-8", errors="replace")
    mod = parse_text(text)
    mod.file_path = str(path)
    if not mod.name or mod.name == "Untitled Mod":
        mod.name = path.stem

    # Try BLIMP tags if standard header didn't find metadata
    try:
        from blimp import parse_blimp_tags
        # Collect the first comment block
        comment_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                comment_lines.append(stripped)
            elif not stripped:
                continue  # skip blank lines at top
            else:
                break  # stop at first non-comment line

        if comment_lines:
            blimp = parse_blimp_tags("\n".join(comment_lines))
            # Only override if BLIMP found values and our header didn't
            if blimp.title and not mod.name:
                mod.name = blimp.title
            if blimp.author and not mod.author:
                mod.author = blimp.author
            if blimp.version and not mod.version:
                mod.version = blimp.version
            if blimp.description and not mod.description:
                mod.description = blimp.description
            if blimp.license_name and not mod.license_name:
                mod.license_name = blimp.license_name
            if blimp.license_url and not mod.license_url:
                mod.license_url = blimp.license_url
            if blimp.contact and not mod.contact:
                mod.contact = blimp.contact
            if blimp.categories and not mod.categories_tag:
                mod.categories_tag = blimp.categories
    except ImportError:
        pass  # blimp module not available

    return mod


def parse_text(text: str) -> ModFile:
    """Parse hotfix mod text content into a ModFile."""
    lines = text.splitlines()
    mod = ModFile()

    # Phase 1: Extract header metadata
    header_end = _parse_header(lines, mod)

    # Phase 2: Parse the body into a category tree
    _parse_body(lines, header_end, mod)

    return mod


def _parse_header(lines: list[str], mod: ModFile) -> int:
    """
    Parse the ### header block at the top of the file.
    Returns the index of the first non-header line.
    """
    i = 0
    in_header = True
    description_lines = []

    while i < len(lines) and in_header:
        line = lines[i].strip()

        # Empty line after header block ends the header
        if not line and i > 0:
            # Check if next non-empty line is still a ### comment
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("###"):
                # Still in header region (description paragraph)
                i += 1
                continue
            else:
                in_header = False
                continue

        if not line.startswith("###") and not line.startswith("#"):
            # Non-comment line = end of header
            in_header = False
            continue

        # Try matching metadata
        meta_match = META_RE.match(line)
        if meta_match:
            key = meta_match.group(1).lower()
            val = meta_match.group(2).strip()
            if key == "name":
                mod.name = val
            elif key == "version":
                mod.version = val
            elif key == "author":
                mod.author = val
            elif key == "contact":
                mod.contact = val
            elif key == "categories":
                mod.categories_tag = val
            elif key == "license":
                mod.license_name = val
            elif key == "license url":
                mod.license_url = val
            i += 1
            continue

        # Check if it's a section header (##### or ### NAME ###)
        if MAJOR_HEADER_RE.match(line) or SECTION_NAME_RE.match(line):
            in_header = False
            continue

        if SUBSECTION_RE.match(line):
            in_header = False
            continue

        # It's a ### comment line that's part of the description/credits
        content = line.lstrip("#").strip()
        if content:
            description_lines.append(content)
        else:
            description_lines.append("")

        i += 1

    mod.description = "\n".join(description_lines).strip()
    return i


def _parse_body(lines: list[str], start: int, mod: ModFile):
    """
    Parse the body of the file into categories and entries.

    The structure uses comment patterns to define hierarchy:
    - ######...###### blocks with ### NAME ### = major category
    - ### NAME ### alone = subcategory
    - # comment above a hotfix line = entry comment
    """
    i = start
    n = len(lines)

    current_major: Category | None = None
    current_sub: Category | None = None
    pending_comments: list[str] = []

    while i < n:
        line = lines[i].strip()

        # Skip empty lines (but keep pending comments)
        if not line:
            i += 1
            continue

        # Check for major section header (3-line block: ####, ### NAME ###, ####)
        if MAJOR_HEADER_RE.match(line):
            # Look ahead for the name line
            if i + 1 < n:
                name_match = SECTION_NAME_RE.match(lines[i + 1].strip())
                if name_match:
                    section_name = name_match.group(1).strip()
                    # Skip the closing #### line too
                    skip_to = i + 2
                    if skip_to < n and MAJOR_HEADER_RE.match(lines[skip_to].strip()):
                        skip_to += 1

                    current_major = Category(name=section_name)
                    mod.root.add_child(current_major)
                    current_sub = None
                    pending_comments.clear()
                    i = skip_to
                    continue

            # Standalone #### line — skip
            i += 1
            continue

        # Check for subsection header: ### NAME ###
        sub_match = SUBSECTION_RE.match(line)
        if sub_match:
            sub_name = sub_match.group(1).strip()

            # If no major category yet, create one
            if current_major is None:
                current_major = Category(name="General")
                mod.root.add_child(current_major)

            current_sub = Category(name=sub_name)
            current_major.add_child(current_sub)
            pending_comments.clear()
            i += 1
            continue

        # Check for hotfix entry
        if is_hotfix_line(line):
            comment_text = "\n".join(pending_comments).strip()

            # Convert simple commands to Spark format
            raw_line = _maybe_convert_simple(line)

            entry = HotfixEntry(
                raw_line=raw_line,
                comment=comment_text,
                enabled=True,
            )

            # Add to the deepest current category
            target = current_sub or current_major
            if target is None:
                target = Category(name="General")
                mod.root.add_child(target)
                current_major = target

            target.add_child(entry)
            pending_comments.clear()
            i += 1
            continue

        # Check for disabled (commented-out) hotfix entry: #SparkPatchEntry,... or ##DISABLED## SparkPatchEntry,...
        disabled_line = None
        if line.startswith("#") and not line.startswith("##"):
            # Single # prefix — check if the rest is a Spark hotfix (not simple commands,
            # because "# Set the barrel mesh" is a comment, not a disabled "set" command)
            inner = line[1:].strip()
            # Only treat as disabled if it starts with a Spark type or has comma-separated fields
            is_spark_disabled = any(inner.startswith(ht + ",") or inner == ht for ht in HOTFIX_TYPES)
            if is_spark_disabled:
                disabled_line = inner
        elif line.startswith("##DISABLED##"):
            inner = line[len("##DISABLED##"):].strip()
            if inner:
                disabled_line = inner

        if disabled_line is not None:
            comment_text = "\n".join(pending_comments).strip()
            raw_line = _maybe_convert_simple(disabled_line)

            entry = HotfixEntry(
                raw_line=raw_line,
                comment=comment_text,
                enabled=False,
            )

            target = current_sub or current_major
            if target is None:
                target = Category(name="General")
                mod.root.add_child(target)
                current_major = target

            target.add_child(entry)
            pending_comments.clear()
            i += 1
            continue

        # It's a comment line — collect it
        if line.startswith("#"):
            content = line.lstrip("#").strip()
            pending_comments.append(content)
            i += 1
            continue

        # Unknown line — treat as comment
        pending_comments.append(line)
        i += 1

    # Clean up empty categories
    _prune_empty(mod.root)


def _prune_empty(cat: Category):
    """Remove empty categories (no entries anywhere in subtree)."""
    for child in list(cat.children):
        if isinstance(child, Category):
            _prune_empty(child)
            if not child.children:
                cat.children.remove(child)