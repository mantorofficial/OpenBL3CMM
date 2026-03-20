"""
BLIMP (BL Mod Parser) tag support.

BLIMP tags are metadata embedded in comment blocks at the top of mod files.
Format: @tag_name value

Supported tags:
  @title       - Mod title
  @author      - Mod author(s)
  @main-author - Primary author
  @version     - Mod version string
  @description - Mod description (multiple lines joined)
  @game        - Target game(s): BL2, TPS, AoDK, BL3, WL, BL4
  @license     - License name
  @license-url - License URL
  @contact     - Contact info
  @categories  - Mod categories/tags
  @nexus-id    - Nexus Mods ID
  @url         - Mod URL
  @hidden      - If present, hides mod from listings

Reference: https://github.com/apple1417/blcmm-parsing/tree/master/blimp
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# All known BLIMP tags
BLIMP_TAGS = {
    "title", "author", "main-author", "version", "description",
    "game", "license", "license-url", "contact", "categories",
    "nexus-id", "url", "hidden",
}


@dataclass
class BlimpMetadata:
    """Parsed BLIMP metadata from a mod file."""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    main_author: str = ""
    version: str = ""
    description: str = ""
    games: list[str] = field(default_factory=list)
    license_name: str = ""
    license_url: str = ""
    contact: str = ""
    categories: str = ""
    nexus_id: str = ""
    url: str = ""
    hidden: bool = False

    @property
    def author(self) -> str:
        """Combined author string."""
        parts = []
        if self.main_author:
            parts.append(self.main_author)
        parts.extend(a for a in self.authors if a != self.main_author)
        return ", ".join(parts) if parts else ""


def parse_blimp_tags(comment_block: str) -> BlimpMetadata:
    """
    Parse BLIMP tags from a comment block (lines starting with #).
    Returns a BlimpMetadata with all found tags.
    """
    meta = BlimpMetadata()
    desc_parts: list[str] = []

    for line in comment_block.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if not stripped.startswith("@"):
            continue

        # Parse @tag value
        match = re.match(r"@([\w-]+)\s*(.*)", stripped)
        if not match:
            continue

        tag = match.group(1).lower()
        value = match.group(2).strip()

        if tag == "title":
            meta.title = value
        elif tag == "author":
            if value:
                meta.authors.append(value)
        elif tag == "main-author":
            meta.main_author = value
        elif tag == "version":
            meta.version = value
        elif tag == "description":
            if not value:
                # Empty @description = newline separator
                desc_parts.append("\n")
            else:
                desc_parts.append(value)
        elif tag == "game":
            for g in re.split(r"[,\s]+", value):
                g = g.strip()
                if g:
                    meta.games.append(g)
        elif tag == "license":
            meta.license_name = value
        elif tag == "license-url":
            meta.license_url = value
        elif tag == "contact":
            meta.contact = value
        elif tag == "categories":
            meta.categories = value
        elif tag == "nexus-id":
            meta.nexus_id = value
        elif tag == "url":
            meta.url = value
        elif tag == "hidden":
            meta.hidden = True

    # Join description parts
    if desc_parts:
        result = []
        for part in desc_parts:
            if part == "\n":
                result.append("\n")
            else:
                if result and result[-1] != "\n":
                    result.append(" ")
                result.append(part)
        meta.description = "".join(result).strip()

    return meta


def generate_blimp_block(meta: BlimpMetadata) -> str:
    """
    Generate a BLIMP comment block from metadata.
    Returns lines prefixed with '#'.
    """
    lines = []

    if meta.title:
        lines.append(f"@title {meta.title}")
    if meta.main_author:
        lines.append(f"@main-author {meta.main_author}")
    for author in meta.authors:
        if author != meta.main_author:
            lines.append(f"@author {author}")
    if not meta.main_author and meta.authors:
        # Already added via the loop above
        pass
    if meta.version:
        lines.append(f"@version {meta.version}")
    if meta.description:
        for desc_line in meta.description.split("\n"):
            desc_line = desc_line.strip()
            if desc_line:
                lines.append(f"@description {desc_line}")
            else:
                lines.append("@description")
    if meta.games:
        lines.append(f"@game {', '.join(meta.games)}")
    if meta.license_name:
        lines.append(f"@license {meta.license_name}")
    if meta.license_url:
        lines.append(f"@license-url {meta.license_url}")
    if meta.contact:
        lines.append(f"@contact {meta.contact}")
    if meta.categories:
        lines.append(f"@categories {meta.categories}")
    if meta.nexus_id:
        lines.append(f"@nexus-id {meta.nexus_id}")
    if meta.url:
        lines.append(f"@url {meta.url}")
    if meta.hidden:
        lines.append("@hidden")

    return "\n".join(f"# {line}" for line in lines)
