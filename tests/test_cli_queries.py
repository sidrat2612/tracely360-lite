"""The query, path and explain CLI commands read graph.json with either node-link edges key."""
import json
import subprocess
import sys

import networkx as nx
import pytest
from networkx.readwrite import json_graph


@pytest.fixture(params=["links", "edges"])
def graph_file(request, tmp_path):
    G = nx.Graph()
    G.add_node("n1", label="extract", source_file="extract.py", source_location="L1")
    G.add_node("n2", label="cluster", source_file="cluster.py", source_location="L2")
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED")
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(json_graph.node_link_data(G, edges=request.param)))
    return path


def _cli(*args):
    return subprocess.run([sys.executable, "-m", "tracely360", *args], capture_output=True, text=True)


def test_explain(graph_file):
    result = _cli("explain", "extract", "--graph", str(graph_file))
    assert result.returncode == 0, result.stderr
    assert "--> cluster [calls] [EXTRACTED]" in result.stdout


def test_path(graph_file):
    result = _cli("path", "extract", "cluster", "--graph", str(graph_file))
    assert result.returncode == 0, result.stderr
    assert "Shortest path (1 hops)" in result.stdout


def test_query(graph_file):
    result = _cli("query", "extract", "--graph", str(graph_file))
    assert result.returncode == 0, result.stderr
    assert "EDGE extract --calls [EXTRACTED]--> cluster" in result.stdout
