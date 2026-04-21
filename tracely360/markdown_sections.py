from __future__ import annotations

import re
from pathlib import Path


def append_markdown_section(target: Path, marker: str, section: str) -> bool:
    if target.exists():
        content = target.read_text(encoding="utf-8")
        if marker in content:
            return False
        target.write_text(content.rstrip() + "\n\n" + section, encoding="utf-8")
        return True

    target.write_text(section, encoding="utf-8")
    return True


def remove_markdown_section(target: Path, marker: str) -> str:
    """Remove the markdown section starting at ``marker`` from ``target``.

    Returns:
        ``"missing_file"``: ``target`` does not exist.
        ``"missing_section"``: ``target`` exists but does not contain ``marker``.
        ``"updated"``: the section was removed and the file still contains content.
        ``"deleted"``: the section was removed and the file became empty, so it was deleted.
    """
    if not target.exists():
        return "missing_file"

    content = target.read_text(encoding="utf-8")
    if marker not in content:
        return "missing_section"

    cleaned = re.sub(
        rf"\n*{re.escape(marker)}\n.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()
    if cleaned:
        target.write_text(cleaned + "\n", encoding="utf-8")
        return "updated"

    target.unlink()
    return "deleted"