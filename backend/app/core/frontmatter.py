from __future__ import annotations

import yaml


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split YAML frontmatter from a markdown file.

    Returns (metadata, body) where metadata is a dict (empty if no frontmatter)
    and body is the text after the closing --- delimiter.
    """
    if not text.startswith("---"):
        return {}, text

    # Find the closing --- (must be on its own line, not the opening one)
    rest = text[3:]
    close = rest.find("\n---")
    if close == -1:
        return {}, text

    raw_yaml = rest[:close].strip()
    body = rest[close + 4:].lstrip("\n")

    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        meta = {}

    return meta, body
