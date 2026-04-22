from __future__ import annotations

import re
import unicodedata

_INVALID_NOTE_CHARS_RE = re.compile(r'[\\/*?:"<>|#^[\]]')
_MARKDOWN_SUFFIX_RE = re.compile(r"\.(md|mdx|markdown)$", flags=re.IGNORECASE)


def normalize_inline_text(text: str) -> str:
    """Normalize multi-line text to a single line and trim surrounding whitespace."""
    return text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()


def strip_diacritics(text: str) -> str:
    """Return text with diacritics removed via NFKD normalization."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def safe_note_name(label: str, fallback: str = "unnamed") -> str:
    """Return a safe note name with invalid filename characters removed."""
    cleaned = normalize_inline_text(label)
    cleaned = _INVALID_NOTE_CHARS_RE.sub("", cleaned)
    cleaned = _MARKDOWN_SUFFIX_RE.sub("", cleaned)
    return cleaned or fallback


def safe_wiki_filename(label: str, fallback: str = "unnamed") -> str:
    cleaned = normalize_inline_text(label)
    cleaned = cleaned.replace("/", "-").replace(" ", "_").replace(":", "-")
    cleaned = _INVALID_NOTE_CHARS_RE.sub("", cleaned)
    cleaned = _MARKDOWN_SUFFIX_RE.sub("", cleaned)
    return cleaned or fallback