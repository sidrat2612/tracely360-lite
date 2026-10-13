"""Graph query operations as library functions.

The MCP server (``serve.py``) renders these as text for agents; other callers use them
directly. Each function takes a graph as produced by ``build_from_json()`` or loaded from
``graph.json`` and returns plain, JSON-serializable data. The graph is undirected, so edges
are reported in traversal or path order rather than extraction direction.
"""
from __future__ import annotations
import unicodedata
import networkx as nx

MAX_DEPTH = 6
CONFIDENCES = ("EXTRACTED", "INFERRED", "AMBIGUOUS")


def _communities_from_graph(G: nx.Graph) -> dict[int, list[str]]:
    """Reconstruct community dict from community property stored on nodes."""
    communities: dict[int, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        cid = data.get("community")
        if cid is not None:
            communities.setdefault(int(cid), []).append(node_id)
    return communities


def _strip_diacritics(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _score_nodes(G: nx.Graph, terms: list[str]) -> list[tuple[float, str]]:
    scored = []
    norm_terms = [_strip_diacritics(t).lower() for t in terms]
    for nid, data in G.nodes(data=True):
        norm_label = data.get("norm_label") or _strip_diacritics(data.get("label") or "").lower()
        source = (data.get("source_file") or "").lower()
        score = sum(1 for t in norm_terms if t in norm_label) + sum(0.5 for t in norm_terms if t in source)
        if score > 0:
            scored.append((score, nid))
    return sorted(scored, reverse=True)


def _bfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:
    visited: set[str] = set(start_nodes)
    frontier = set(start_nodes)
    edges_seen: list[tuple] = []
    for _ in range(depth):
        next_frontier: set[str] = set()
        for n in sorted(frontier):  # sorted: edge order must not depend on set iteration
            for neighbor in G.neighbors(n):
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    edges_seen.append((n, neighbor))
        visited.update(next_frontier)
        frontier = next_frontier
    return visited, edges_seen


def _dfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:
    visited: set[str] = set()
    edges_seen: list[tuple] = []
    stack = [(n, 0) for n in reversed(start_nodes)]
    while stack:
        node, d = stack.pop()
        if node in visited or d > depth:
            continue
        visited.add(node)
        for neighbor in G.neighbors(node):
            if neighbor not in visited:
                stack.append((neighbor, d + 1))
                edges_seen.append((node, neighbor))
    return visited, edges_seen


def _find_node(G: nx.Graph, label: str) -> list[str]:
    """Return node IDs whose label or ID matches the search term (diacritic-insensitive)."""
    term = _strip_diacritics(label).lower()
    return [nid for nid, d in G.nodes(data=True)
            if term in (d.get("norm_label") or _strip_diacritics(d.get("label") or "").lower())
            or term == nid.lower()]


def query_graph(G: nx.Graph, question: str, mode: str = "bfs", depth: int = 3) -> dict:
    """Traverse the graph from the nodes that best match the question's keywords.

    Words longer than two characters are matched against labels and source files; the
    three best-scoring nodes start a breadth-first (``bfs``) or depth-first (``dfs``)
    traversal of at most ``depth`` hops (capped at 6).

    Returns:
        {
          "mode": "bfs", "depth": 3,
          "start": [node ids],
          "nodes": [node ids, most connected first],
          "edges": [(u, v), ...]   # in traversal order
        }
        ``start`` is empty when nothing matches.
    """
    if mode not in ("bfs", "dfs"):
        raise ValueError(f"mode must be 'bfs' or 'dfs', got {mode!r}")
    depth = min(int(depth), MAX_DEPTH)
    terms = [t.lower() for t in question.split() if len(t) > 2]
    start = [nid for _, nid in _score_nodes(G, terms)[:3]]
    if not start:
        return {"mode": mode, "depth": depth, "start": [], "nodes": [], "edges": []}
    nodes, edges = _dfs(G, start, depth) if mode == "dfs" else _bfs(G, start, depth)
    return {
        "mode": mode,
        "depth": depth,
        "start": start,
        "nodes": sorted(nodes, key=lambda n: (-G.degree(n), n)),
        "edges": edges,
    }


def get_node(G: nx.Graph, label: str) -> dict | None:
    """Details of the first node whose label contains ``label`` or whose ID equals it.

    Returns {"id", "label", "source_file", "source_location", "file_type", "community",
    "degree"}, or None when nothing matches. ``community`` is None for unclustered nodes.
    """
    term = label.lower()
    for nid, d in G.nodes(data=True):
        if term in (d.get("label") or "").lower() or term == nid.lower():
            return {
                "id": nid,
                "label": d.get("label", nid),
                "source_file": d.get("source_file", ""),
                "source_location": d.get("source_location", ""),
                "file_type": d.get("file_type", ""),
                "community": d.get("community"),
                "degree": G.degree(nid),
            }
    return None


def get_neighbors(G: nx.Graph, label: str, relation_filter: str | None = None) -> dict | None:
    """Direct neighbors of the first node matching ``label`` (diacritic-insensitive).

    ``relation_filter`` keeps edges whose relation contains it (case-insensitive).

    Returns {"id", "label", "neighbors": [{"id", "label", "relation", "confidence"}]},
    or None when no node matches.
    """
    matches = _find_node(G, label)
    if not matches:
        return None
    nid = matches[0]
    wanted = (relation_filter or "").lower()
    neighbors = []
    for neighbor in G.neighbors(nid):
        d = G.edges[nid, neighbor]
        relation = d.get("relation", "")
        if wanted and wanted not in relation.lower():
            continue
        neighbors.append({
            "id": neighbor,
            "label": G.nodes[neighbor].get("label", neighbor),
            "relation": relation,
            "confidence": d.get("confidence", ""),
        })
    return {"id": nid, "label": G.nodes[nid].get("label", nid), "neighbors": neighbors}


def get_community(
    G: nx.Graph, community_id: int, communities: dict[int, list[str]] | None = None
) -> list[dict]:
    """Members of a community: [{"id", "label", "source_file"}]; empty when it does not exist.

    ``communities`` may be passed to avoid recomputing it from the nodes' ``community`` field.
    """
    if communities is None:
        communities = _communities_from_graph(G)
    return [
        {"id": n, "label": G.nodes[n].get("label", n), "source_file": G.nodes[n].get("source_file", "")}
        for n in communities.get(int(community_id), [])
    ]


def graph_stats(G: nx.Graph, communities: dict[int, list[str]] | None = None) -> dict:
    """Node, edge and community counts, and edges per confidence class.

    Returns {"nodes", "edges", "communities", "confidence": {"EXTRACTED": n, "INFERRED": n,
    "AMBIGUOUS": n, ...}}. Edges without a confidence count as EXTRACTED; any other value
    found is counted under its own name.
    """
    if communities is None:
        communities = _communities_from_graph(G)
    confidence = dict.fromkeys(CONFIDENCES, 0)
    for _, _, d in G.edges(data=True):
        value = d.get("confidence", "EXTRACTED")
        confidence[value] = confidence.get(value, 0) + 1
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "communities": len(communities),
        "confidence": confidence,
    }


def shortest_path(G: nx.Graph, source: str, target: str, max_hops: int = 8) -> dict:
    """Shortest path between the best keyword matches for ``source`` and ``target``.

    Returns {"status", "source", "target", "hops", "path", "edges"} where ``status`` is
    ``ok``, ``no_source`` or ``no_target`` (nothing matches), ``no_path``, or ``too_long``
    (the shortest path has more than ``max_hops`` hops; ``hops`` says how many). ``path``
    lists node IDs and ``edges`` holds {"source", "target", "relation", "confidence"} in
    path order; both are empty unless ``status`` is ``ok``.
    """
    result: dict = {"status": "ok", "source": None, "target": None, "hops": None, "path": [], "edges": []}
    src_scored = _score_nodes(G, [t.lower() for t in source.split()])
    if not src_scored:
        return {**result, "status": "no_source"}
    tgt_scored = _score_nodes(G, [t.lower() for t in target.split()])
    if not tgt_scored:
        return {**result, "status": "no_target"}
    result["source"], result["target"] = src_scored[0][1], tgt_scored[0][1]
    max_hops = int(max_hops)
    try:
        path = nx.shortest_path(G, result["source"], result["target"])
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {**result, "status": "no_path"}
    result["hops"] = len(path) - 1
    if result["hops"] > max_hops:
        return {**result, "status": "too_long"}
    result["path"] = path
    for u, v in zip(path, path[1:]):
        d = G.edges[u, v]
        result["edges"].append({
            "source": u,
            "target": v,
            "relation": d.get("relation", ""),
            "confidence": d.get("confidence", ""),
        })
    return result
