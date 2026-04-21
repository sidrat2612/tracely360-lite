from __future__ import annotations

import re
import unicodedata

_INVALID_NOTE_CHARS_RE = re.compile(r'[\\/*?:"<>|#^[\]]')
_MARKDOWN_SUFFIX_RE = re.compile(r"\.(md|mdx|markdown)$", flags=re.IGNORECASE)


def normalize_inline_text(text: str) -> str:
    """Normalize multi-line text to a single line by replacing line breaks with spaces and trimming surrounding whitespace."""
    return text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()

def strip_diacritics(text: str) -> str:
    """Return text with diacritics removed via NFKD normalization.

    The input is first normalized with Unicode NFKD decomposition, then
    combining characters are removed to produce text safer for ASCII-oriented
    naming contexts.
    """
def strip_diacritics(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def safe_wiki_filename(label: str, fallback: str = "unnamed") -> str:
    """Return a wiki-safe filename derived from ``label``.

    Normalizes inline whitespace, replaces spaces with underscores, and
    replaces forward slashes and colons with dashes. If the transformed
    filename is empty, returns ``fallback`` instead.
    """
    cleaned = normalize_inline_text(label)
    cleaned = _INVALID_NOTE_CHARS_RE.sub("", cleaned)
    cleaned = _MARKDOWN_SUFFIX_RE.sub("", cleaned)
    return cleaned or fallback


def safe_wiki_filename(label: str, fallback: str = "unnamed") -> str:
    cleaned = normalize_inline_text(label)
    cleaned = cleaned.replace("/", "-").replace(" ", "_").replace(":", "-")
    return cleaned or fallback