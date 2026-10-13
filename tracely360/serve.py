# MCP stdio server - exposes graph query tools to Claude and other agents
from __future__ import annotations
import json
import sys
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph
from tracely360.security import sanitize_label
from tracely360.query import (  # noqa: F401 - helpers re-exported for the CLI and tests
    _bfs,
    _communities_from_graph,
    _dfs,
    _find_node,
    _score_nodes,
    _strip_diacritics,
    get_community,
    get_neighbors,
    get_node,
    graph_stats,
    query_graph,
    shortest_path,
)


def _load_graph(graph_path: str) -> nx.Graph:
    try:
        resolved = Path(graph_path).resolve()
        if resolved.suffix != ".json":
            raise ValueError(f"Graph path must be a .json file, got: {graph_path!r}")
        if not resolved.exists():
            raise FileNotFoundError(f"Graph file not found: {resolved}")
        safe = resolved
        data = json.loads(safe.read_text(encoding="utf-8"))
        try:
            return json_graph.node_link_graph(data, edges="links")
        except TypeError:
            return json_graph.node_link_graph(data)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"error: graph.json is corrupted ({exc}). Re-run /tracely360 to rebuild.", file=sys.stderr)
        sys.exit(1)


def _subgraph_to_text(G: nx.Graph, nodes: set[str] | list[str], edges: list[tuple], token_budget: int = 2000) -> str:
    """Render subgraph as text, cutting at token_budget (approx 3 chars/token)."""
    char_budget = token_budget * 3
    lines = []
    node_set = set(nodes)
    for nid in sorted(nodes, key=lambda n: G.degree(n), reverse=True):
        d = G.nodes[nid]
        line = f"NODE {sanitize_label(d.get('label', nid))} [src={d.get('source_file', '')} loc={d.get('source_location', '')} cluster={d.get('community', '')}]"
        lines.append(line)
    for u, v in edges:
        if u in node_set and v in node_set:
            raw = G[u][v]
            d = next(iter(raw.values()), {}) if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)) else raw
            line = f"EDGE {sanitize_label(G.nodes[u].get('label', u))} --{d.get('relation', '')} [{d.get('confidence', '')}]--> {sanitize_label(G.nodes[v].get('label', v))}"
            lines.append(line)
    output = "\n".join(lines)
    if len(output) > char_budget:
        output = output[:char_budget] + f"\n... (truncated to ~{token_budget} token budget)"
    return output


def _filter_blank_stdin() -> None:
    """Filter blank lines from stdin before MCP reads it.

    Some MCP clients (Claude Desktop, etc.) send blank lines between JSON
    messages. The MCP stdio transport tries to parse every line as a
    JSONRPCMessage, so a bare newline triggers a Pydantic ValidationError.
    This installs an OS-level pipe that relays stdin while dropping blanks.
    """
    import os
    import threading

    r_fd, w_fd = os.pipe()
    saved_fd = os.dup(sys.stdin.fileno())

    def _relay() -> None:
        try:
            with open(saved_fd, "rb") as src, open(w_fd, "wb") as dst:
                for line in src:
                    if line.strip():
                        dst.write(line)
                        dst.flush()
        except Exception:
            pass

    threading.Thread(target=_relay, daemon=True).start()
    os.dup2(r_fd, sys.stdin.fileno())
    os.close(r_fd)
    sys.stdin = open(0, "r", closefd=False)


def _tool_handlers(G: nx.Graph, communities: dict[int, list[str]]) -> dict:
    """The MCP tools as text renderers over the tracely360.query library functions."""

    def _tool_query_graph(arguments: dict) -> str:
        question = arguments["question"]
        mode = arguments.get("mode", "bfs")
        depth = min(int(arguments.get("depth", 3)), 6)
        budget = int(arguments.get("token_budget", 2000))
        result = query_graph(G, question, mode="dfs" if mode == "dfs" else "bfs", depth=depth)
        if not result["start"]:
            return "No matching nodes found."
        header = f"Traversal: {mode.upper()} depth={depth} | Start: {[G.nodes[n].get('label', n) for n in result['start']]} | {len(result['nodes'])} nodes found\n\n"
        return header + _subgraph_to_text(G, result["nodes"], result["edges"], budget)

    def _tool_get_node(arguments: dict) -> str:
        label = arguments["label"].lower()
        node = get_node(G, label)
        if node is None:
            return f"No node matching '{label}' found."
        community = "" if node["community"] is None else node["community"]
        return "\n".join([
            f"Node: {node['label']}",
            f"  ID: {node['id']}",
            f"  Source: {node['source_file']} {node['source_location']}",
            f"  Type: {node['file_type']}",
            f"  Cluster: {community}",
            f"  Degree: {node['degree']}",
        ])

    def _tool_get_neighbors(arguments: dict) -> str:
        label = arguments["label"].lower()
        rel_filter = arguments.get("relation_filter", "").lower()
        result = get_neighbors(G, label, rel_filter)
        if result is None:
            return f"No node matching '{label}' found."
        lines = [f"Neighbors of {result['label']}:"]
        for n in result["neighbors"]:
            lines.append(f"  --> {n['label']} [{n['relation']}] [{n['confidence']}]")
        return "\n".join(lines)

    def _tool_get_community(arguments: dict) -> str:
        cid = int(arguments["community_id"])
        members = get_community(G, cid, communities)
        if not members:
            return f"Cluster {cid} not found."
        lines = [f"Cluster {cid} ({len(members)} nodes):"]
        for m in members:
            lines.append(f"  {m['label']} [{m['source_file']}]")
        return "\n".join(lines)

    def _tool_god_nodes(arguments: dict) -> str:
        from .analyze import god_nodes as _god_nodes
        nodes = _god_nodes(G, top_n=int(arguments.get("top_n", 10)))
        lines = ["God nodes (most connected):"]
        lines += [f"  {i}. {n['label']} - {n['degree']} edges" for i, n in enumerate(nodes, 1)]
        return "\n".join(lines)

    def _tool_graph_stats(_: dict) -> str:
        stats = graph_stats(G, communities)
        confidence = stats["confidence"]
        total = stats["edges"] or 1
        return (
            f"Nodes: {stats['nodes']}\n"
            f"Edges: {stats['edges']}\n"
            f"Clusters: {stats['communities']}\n"
            f"EXTRACTED: {round(confidence['EXTRACTED']/total*100)}%\n"
            f"INFERRED: {round(confidence['INFERRED']/total*100)}%\n"
            f"AMBIGUOUS: {round(confidence['AMBIGUOUS']/total*100)}%\n"
        )

    def _tool_shortest_path(arguments: dict) -> str:
        result = shortest_path(G, arguments["source"], arguments["target"], arguments.get("max_hops", 8))
        status = result["status"]
        if status == "no_source":
            return f"No node matching source '{arguments['source']}' found."
        if status == "no_target":
            return f"No node matching target '{arguments['target']}' found."
        src, tgt = result["source"], result["target"]
        if status == "no_path":
            return f"No path found between '{G.nodes[src].get('label', src)}' and '{G.nodes[tgt].get('label', tgt)}'."
        if status == "too_long":
            return f"Path exceeds max_hops={int(arguments.get('max_hops', 8))} ({result['hops']} hops found)."
        segments = [G.nodes[src].get("label", src)] if result["edges"] else []
        for edge in result["edges"]:
            conf_str = f" [{edge['confidence']}]" if edge["confidence"] else ""
            segments.append(f"--{edge['relation']}{conf_str}--> {G.nodes[edge['target']].get('label', edge['target'])}")
        return f"Shortest path ({result['hops']} hops):\n  " + " ".join(segments)

    return {
        "query_graph": _tool_query_graph,
        "get_node": _tool_get_node,
        "get_neighbors": _tool_get_neighbors,
        "get_community": _tool_get_community,
        "god_nodes": _tool_god_nodes,
        "graph_stats": _tool_graph_stats,
        "shortest_path": _tool_shortest_path,
    }


def serve(graph_path: str = "tracely360-out/graph.json") -> None:
    """Start the MCP server. Requires pip install mcp."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError as e:
        raise ImportError("mcp not installed. Run: pip install mcp") from e

    G = _load_graph(graph_path)
    communities = _communities_from_graph(G)

    server = Server("tracely360")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="query_graph",
                description="Search the knowledge graph using BFS or DFS. Returns relevant nodes and edges as text context.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Natural language question or keyword search"},
                        "mode": {"type": "string", "enum": ["bfs", "dfs"], "default": "bfs",
                                 "description": "bfs=broad context, dfs=trace a specific path"},
                        "depth": {"type": "integer", "default": 3, "description": "Traversal depth (1-6)"},
                        "token_budget": {"type": "integer", "default": 2000, "description": "Max output tokens"},
                    },
                    "required": ["question"],
                },
            ),
            types.Tool(
                name="get_node",
                description="Get full details for a specific node by label or ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"label": {"type": "string", "description": "Node label or ID to look up"}},
                    "required": ["label"],
                },
            ),
            types.Tool(
                name="get_neighbors",
                description="Get all direct neighbors of a node with edge details.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "relation_filter": {"type": "string", "description": "Optional: filter by relation type"},
                    },
                    "required": ["label"],
                },
            ),
            types.Tool(
                name="get_community",
                description="Get all nodes in a cluster by community ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"community_id": {"type": "integer", "description": "Cluster ID (0-indexed by size)"}},
                    "required": ["community_id"],
                },
            ),
            types.Tool(
                name="god_nodes",
                description="Return the most connected nodes - the core abstractions of the knowledge graph.",
                inputSchema={"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}},
            ),
            types.Tool(
                name="graph_stats",
                description="Return summary statistics: node count, edge count, communities, confidence breakdown.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="shortest_path",
                description="Find the shortest path between two concepts in the knowledge graph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source concept label or keyword"},
                        "target": {"type": "string", "description": "Target concept label or keyword"},
                        "max_hops": {"type": "integer", "default": 8, "description": "Maximum hops to consider"},
                    },
                    "required": ["source", "target"],
                },
            ),
        ]

    _handlers = _tool_handlers(G, communities)

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        handler = _handlers.get(name)
        if not handler:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            return [types.TextContent(type="text", text=handler(arguments))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Error executing {name}: {exc}")]

    import asyncio

    async def main() -> None:
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    _filter_blank_stdin()
    asyncio.run(main())


if __name__ == "__main__":
    graph_path = sys.argv[1] if len(sys.argv) > 1 else "tracely360-out/graph.json"
    serve(graph_path)
