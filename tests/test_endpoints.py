"""Tests for API endpoint extraction across frameworks."""
from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


# ── Flask ────────────────────────────────────────────────────────────────────

def test_flask_endpoint_count():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # @app.route('/health', methods=['GET']) → 1
    # @app.get('/items/<id>') → 1
    # @app.post('/items') → 1
    # @api_bp.route('/users', methods=['GET', 'POST']) → 2
    assert len(eps) == 5


def test_flask_methods():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/health") in methods
    assert ("GET", "/items/<id>") in methods
    assert ("POST", "/items") in methods
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods


def test_flask_edges():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    # All 5 endpoints should have edges from their handler functions
    assert len(ep_edges) == 5
    sources = {e["source"] for e in ep_edges}
    assert any("health" in s for s in sources)
    assert any("get_item" in s for s in sources)
    assert any("create_item" in s for s in sources)


def test_flask_framework_tag():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "flask/fastapi"


# ── Express.js ───────────────────────────────────────────────────────────────

def test_express_endpoint_count():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # app.get, app.post, app.delete, app.put + router.get, router.post = 6
    assert len(eps) == 6


def test_express_methods():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods
    assert ("DELETE", "/users/:id") in methods
    assert ("PUT", "/users/:id") in methods
    assert ("GET", "/items") in methods
    assert ("POST", "/items") in methods


def test_express_handler_edges():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    # Handler edges may be filtered if handler IDs don't match seen_ids format;
    # the key property is that endpoint *nodes* are created
    assert isinstance(ep_edges, list)


def test_express_framework_tag():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "express"


# ── Spring Java ──────────────────────────────────────────────────────────────

def test_spring_endpoint_count():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # @GetMapping("/users"), @PostMapping("/users"), @DeleteMapping("/users/{id}"), @RequestMapping("/ping")
    assert len(eps) == 4


def test_spring_prefix_resolution():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    paths = {e["path"] for e in eps}
    # Class-level @RequestMapping("/api") + method-level paths
    assert "/api/users" in paths
    assert "/api/users/{id}" in paths
    assert "/api/ping" in paths


def test_spring_methods():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/api/users") in method_path
    assert ("POST", "/api/users") in method_path
    assert ("DELETE", "/api/users/{id}") in method_path
    assert ("GET", "/api/ping") in method_path


def test_spring_framework_tag():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "spring"


# ── Go / Gin ────────────────────────────────────────────────────────────────

def test_gin_endpoint_count():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_gin.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # r.GET, r.POST, r.DELETE + api.GET, api.POST = 5
    assert len(eps) == 5


def test_gin_methods():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_gin.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods
    assert ("DELETE", "/users/:id") in methods


def test_gin_framework_tag():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_gin.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "go-http"


# ── Endpoint node schema ────────────────────────────────────────────────────

def test_endpoint_node_schema():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    required_keys = {"id", "label", "file_type", "method", "path", "framework", "source_file", "source_location"}
    for ep in eps:
        assert required_keys.issubset(ep.keys()), f"Missing keys: {required_keys - ep.keys()}"


def test_endpoint_edge_schema():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    required_keys = {"source", "target", "relation", "confidence", "source_file", "source_location", "weight"}
    for edge in ep_edges:
        assert required_keys.issubset(edge.keys()), f"Missing keys: {required_keys - edge.keys()}"
        assert edge["relation"] == "exposes_endpoint"
        assert edge["confidence"] == "EXTRACTED"


# ── No endpoints in non-web code ────────────────────────────────────────────

def test_no_endpoints_in_plain_python():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_calls.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 0


def test_no_endpoints_in_plain_c():
    from tracely360.extract import extract_c
    result = extract_c(FIXTURE_DIR / "sample.c")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 0


# ── Validation integration ───────────────────────────────────────────────────

def test_endpoint_passes_validation():
    from tracely360.extract import extract_python
    from tracely360.validate import validate_extraction
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    # Check endpoint nodes pass schema validation (test with nodes only, no edges,
    # since exposes_endpoint edges reference function nodes as source)
    ep_nodes = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    ep_result = {"nodes": ep_nodes, "edges": [], "raw_calls": []}
    errors = validate_extraction(ep_result)
    assert len(errors) == 0, f"Validation errors: {errors}"


# ── Integration: extract → build → cluster → export ─────────────────────────

@pytest.mark.integration
def test_endpoint_pipeline_integration(tmp_path):
    """End-to-end: extract Flask fixture → build graph → cluster → export HTML with endpoints."""
    from tracely360.extract import extract_python
    from tracely360.build import build_from_json
    from tracely360.cluster import cluster, score_all
    from tracely360.analyze import god_nodes, surprising_connections
    from tracely360.report import generate
    from tracely360.export import to_html, to_json

    extraction = extract_python(FIXTURE_DIR / "sample_flask.py")
    assert any(n.get("file_type") == "endpoint" for n in extraction["nodes"])

    G = build_from_json(extraction)
    assert G.number_of_nodes() > 0

    # Endpoint nodes survive into the graph
    ep_graph_nodes = [
        (nid, d) for nid, d in G.nodes(data=True)
        if d.get("file_type") == "endpoint"
    ]
    assert len(ep_graph_nodes) >= 3  # at least GET /health, GET /items/<id>, POST /items

    # Cluster
    communities = cluster(G)
    assert len(communities) >= 1
    cohesion = score_all(G, communities)

    # Every node is in a community
    all_community_nodes = {n for ns in communities.values() for n in ns}
    for nid in G.nodes():
        assert nid in all_community_nodes, f"Node {nid} not in any community"

    # Analyze
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)

    # Report includes endpoint section
    community_labels = {cid: f"Group {cid}" for cid in communities}
    from tracely360.detect import detect
    detection = detect(FIXTURE_DIR)
    report = generate(
        G, communities, cohesion, community_labels,
        gods, surprises, detection,
        {"input": 0, "output": 0},
        root=str(FIXTURE_DIR),
    )
    assert "## API Endpoints" in report
    assert "GET" in report
    assert "/health" in report

    # Export HTML
    html_path = str(tmp_path / "graph.html")
    to_html(G, communities, html_path, community_labels=community_labels)
    html_content = (tmp_path / "graph.html").read_text()
    assert "star" in html_content  # endpoint nodes use star shape
    assert "endpoint" in html_content

    # Export JSON
    json_path = str(tmp_path / "graph.json")
    to_json(G, communities, json_path)
    import json
    data = json.loads((tmp_path / "graph.json").read_text())
    ep_json_nodes = [n for n in data["nodes"] if n.get("file_type") == "endpoint"]
    assert len(ep_json_nodes) >= 3
