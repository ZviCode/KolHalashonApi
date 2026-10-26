from __future__ import annotations

import re

_INVALID_CHARS = re.compile(r"[\\/:*?<>|\x00-\x1f]")
_SPACES = re.compile(r"\s+")


def sanitize_filename(name: str, max_length: int = 180) -> str:
    """Make ``name`` safe to use as a file name on Windows, macOS and Linux.

    Hebrew double quotes (גרשיים) are kept readable as two single quotes.
    """
    cleaned = _INVALID_CHARS.sub("", name).replace('"', "''")
    cleaned = _SPACES.sub(" ", cleaned).strip(" .")
    return cleaned[:max_length].rstrip(" .") or "untitled"
