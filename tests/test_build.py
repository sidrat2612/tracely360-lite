import json
from pathlib import Path
from tracely360.build import build_from_json, build

FIXTURES = Path(__file__).parent / "fixtures"

def load_extraction():
    return json.loads((FIXTURES / "extraction.json").read_text())

def test_build_from_json_node_count():
    G = build_from_json(load_extraction())
    assert G.number_of_nodes() == 4

def test_build_from_json_edge_count():
    G = build_from_json(load_extraction())
    assert G.number_of_edges() == 4

def test_nodes_have_label():
    G = build_from_json(load_extraction())
    assert G.nodes["n_transformer"]["label"] == "Transformer"

def test_edges_have_confidence():
    G = build_from_json(load_extraction())
    data = G.edges["n_attention", "n_concept_attn"]
    assert data["confidence"] == "INFERRED"

def test_ambiguous_edge_preserved():
    G = build_from_json(load_extraction())
    data = G.edges["n_layernorm", "n_concept_attn"]
    assert data["confidence"] == "AMBIGUOUS"

def test_build_merges_multiple_extractions():
    ext1 = {"nodes": [{"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"}],
            "edges": [], "input_tokens": 0, "output_tokens": 0}
    ext2 = {"nodes": [{"id": "n2", "label": "B", "file_type": "document", "source_file": "b.md"}],
            "edges": [{"source": "n1", "target": "n2", "relation": "references",
                       "confidence": "INFERRED", "source_file": "b.md", "weight": 1.0}],
            "input_tokens": 0, "output_tokens": 0}
    G = build([ext1, ext2])
    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1


# --- graph_from_node_link ---

def _node_link(key):
    import networkx as nx
    from networkx.readwrite import json_graph
    G = nx.Graph()
    G.add_edge("a", "b", relation="calls")
    return json_graph.node_link_data(G, edges=key)

def test_graph_from_node_link_reads_links_and_edges():
    from tracely360.build import graph_from_node_link
    for key in ("links", "edges"):
        G = graph_from_node_link(_node_link(key))
        assert G.number_of_edges() == 1 and G.edges["a", "b"]["relation"] == "calls"

def test_graph_from_node_link_rejects_data_without_edges():
    import pytest
    from tracely360.build import graph_from_node_link
    with pytest.raises(ValueError, match="links"):
        graph_from_node_link({"directed": False, "multigraph": False, "graph": {}, "nodes": []})
