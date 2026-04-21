from __future__ import annotations

from tree_sitter import Node


def read_node_text(node: Node, source: bytes) -> str:
    """Return the UTF-8 text covered by a tree-sitter node.

    Args:
        node: The tree-sitter ``Node`` whose byte span will be read.
        source: The full source content as bytes.

    Returns:
        The decoded text for ``source[node.start_byte:node.end_byte]``.
    """
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")