"""Tests for query.py - graph query operations as library functions."""
import json
import os
import subprocess
import sys

import networkx as nx
import pytest

import tracely360
from tracely360.query import (
    get_community,
    get_neighbors,
    get_node,
    graph_stats,
    query_graph,
    shortest_path,
)


def _make_graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("n1", label="extract", source_file="extract.py", source_location="L10", file_type="code", community=0)
    G.add_node("n2", label="cluster", source_file="cluster.py", source_location="L5", file_type="code", community=0)
    G.add_node("n3", label="build", source_file="build.py", source_location="L1", file_type="code", community=1)
    G.add_node("n4", label="report", source_file="report.py", source_location="L1", file_type="document", community=1)
    G.add_node("n5", label="isolated", source_file="other.py", source_location="L1", file_type="code", community=2)
    G.add_node("n6", label="Café Résumé", source_file="cafe.py", source_location="L3", file_type="code", community=1)
    G.add_node("n7", label="README", source_file="README.md", source_location="", file_type="document")
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED")
    G.add_edge("n2", "n3", relation="imports", confidence="EXTRACTED")
    G.add_edge("n3", "n4", relation="uses", confidence="EXTRACTED")
    G.add_edge("n3", "n6", relation="calls", confidence="AMBIGUOUS")
    G.add_edge("n6", "n4", relation="references")
    return G


def test_operations_are_exported_from_the_package():
    for name in ("query_graph", "get_node", "get_neighbors", "get_community", "graph_stats",
                 "shortest_path", "god_nodes", "graph_diff"):
        assert callable(getattr(tracely360, name))


# --- query_graph ---

def test_query_graph_bfs():
    result = query_graph(_make_graph(), "how does extract work", depth=2)
    assert result["mode"] == "bfs"
    assert result["depth"] == 2
    assert result["start"] == ["n1"]
    assert set(result["nodes"]) == {"n1", "n2", "n3"}
    assert result["edges"] == [("n1", "n2"), ("n2", "n3")]


def test_query_graph_nodes_most_connected_first():
    result = query_graph(_make_graph(), "extract", depth=6)
    degrees = [_make_graph().degree(n) for n in result["nodes"]]
    assert degrees == sorted(degrees, reverse=True)
    assert result["nodes"][0] == "n3"


def test_query_graph_dfs():
    result = query_graph(_make_graph(), "extract", mode="dfs", depth=1)
    assert result["mode"] == "dfs"
    assert set(result["nodes"]) == {"n1", "n2"}


def test_query_graph_depth_is_capped():
    assert query_graph(_make_graph(), "extract", depth=50)["depth"] == 6


def test_query_graph_ignores_short_words_and_no_match():
    result = query_graph(_make_graph(), "an of zz")
    assert result == {"mode": "bfs", "depth": 3, "start": [], "nodes": [], "edges": []}


def test_query_graph_diacritic_insensitive():
    assert query_graph(_make_graph(), "cafe")["start"] == ["n6"]


def test_query_graph_rejects_unknown_mode():
    with pytest.raises(ValueError, match="mode"):
        query_graph(_make_graph(), "extract", mode="random")


def test_query_graph_is_deterministic_across_hash_seeds(tmp_path):
    script = (
        "import json, networkx as nx\n"
        "from tracely360.query import query_graph\n"
        "G = nx.Graph()\n"
        "for i in range(40):\n"
        "    G.add_node(f'n{i}', label=f'node{i}')\n"
        "    G.add_edge('n0', f'n{i}', relation='calls')\n"
        "    G.add_edge(f'n{i}', f'n{(i * 7) % 40}', relation='uses')\n"
        "print(json.dumps(query_graph(G, 'node0 node1 node2', depth=3)))\n"
    )
    outputs = set()
    for seed in ("1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        outputs.add(subprocess.run([sys.executable, "-c", script], env=env, check=True,
                                   capture_output=True, text=True).stdout)
    assert len(outputs) == 1


# --- get_node ---

def test_get_node_by_label():
    assert get_node(_make_graph(), "BUILD") == {
        "id": "n3", "label": "build", "source_file": "build.py", "source_location": "L1",
        "file_type": "code", "community": 1, "degree": 3,
    }


def test_get_node_by_id_and_unclustered():
    node = get_node(_make_graph(), "n7")
    assert node["label"] == "README"
    assert node["community"] is None


def test_get_node_missing():
    assert get_node(_make_graph(), "xyzzy") is None


# --- get_neighbors ---

def test_get_neighbors():
    result = get_neighbors(_make_graph(), "build")
    assert result["id"] == "n3"
    assert {n["id"] for n in result["neighbors"]} == {"n2", "n4", "n6"}
    assert {"id": "n6", "label": "Café Résumé", "relation": "calls", "confidence": "AMBIGUOUS"} in result["neighbors"]


def test_get_neighbors_relation_filter_and_missing_confidence():
    result = get_neighbors(_make_graph(), "cafe", relation_filter="REF")
    assert result["neighbors"] == [{"id": "n4", "label": "report", "relation": "references", "confidence": ""}]


def test_get_neighbors_missing():
    assert get_neighbors(_make_graph(), "xyzzy") is None


# --- get_community ---

def test_get_community():
    assert get_community(_make_graph(), 0) == [
        {"id": "n1", "label": "extract", "source_file": "extract.py"},
        {"id": "n2", "label": "cluster", "source_file": "cluster.py"},
    ]


def test_get_community_with_precomputed_communities():
    assert get_community(_make_graph(), 5, {5: ["n5"]}) == [
        {"id": "n5", "label": "isolated", "source_file": "other.py"},
    ]


def test_get_community_missing():
    assert get_community(_make_graph(), 99) == []


# --- graph_stats ---

def test_graph_stats():
    assert graph_stats(_make_graph()) == {
        "nodes": 7,
        "edges": 5,
        "communities": 3,
        "confidence": {"EXTRACTED": 3, "INFERRED": 1, "AMBIGUOUS": 1},
    }


def test_graph_stats_counts_unknown_confidence_and_empty_graph():
    G = nx.Graph()
    assert graph_stats(G)["confidence"] == {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
    G.add_edge("a", "b", confidence="GUESSED")
    assert graph_stats(G)["confidence"]["GUESSED"] == 1


def test_graph_stats_is_json_serializable():
    json.dumps(graph_stats(_make_graph()))


# --- shortest_path ---

def test_shortest_path():
    result = shortest_path(_make_graph(), "extract", "report")
    assert result["status"] == "ok"
    assert result["source"] == "n1"
    assert result["target"] == "n4"
    assert result["hops"] == 3
    assert result["path"] == ["n1", "n2", "n3", "n4"]
    assert result["edges"][0] == {"source": "n1", "target": "n2", "relation": "calls", "confidence": "INFERRED"}
    assert [e["target"] for e in result["edges"]] == ["n2", "n3", "n4"]


def test_shortest_path_too_long():
    result = shortest_path(_make_graph(), "extract", "report", max_hops=2)
    assert result["status"] == "too_long"
    assert result["hops"] == 3
    assert result["path"] == [] and result["edges"] == []


def test_shortest_path_no_path():
    result = shortest_path(_make_graph(), "extract", "isolated")
    assert result["status"] == "no_path"
    assert (result["source"], result["target"], result["hops"]) == ("n1", "n5", None)


def test_shortest_path_no_match():
    assert shortest_path(_make_graph(), "xyzzy", "report")["status"] == "no_source"
    assert shortest_path(_make_graph(), "extract", "xyzzy")["status"] == "no_target"
