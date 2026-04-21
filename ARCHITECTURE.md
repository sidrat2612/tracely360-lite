# Architecture

tracely360-lite is a local knowledge-graph engine packaged behind a CLI, assistant skills, and an optional MCP stdio server. The code path is deterministic for source files; semantic extraction for docs, papers, images, and transcripts is layered on top.

## Runtime pipeline

```text
detect(root)
  → extract(paths)
  → build_from_json() / build()
  → cluster() + score_all()
  → god_nodes() / surprising_connections() / suggest_questions()
  → generate()
  → to_json() / to_html() / to_obsidian()
```

The pipeline passes plain Python dicts and NetworkX graphs between stages. Persistent outputs land under `tracely360-lite-out/`.

## Core modules

| Module | Public entry points | Purpose |
|--------|---------------------|---------|
| `detect.py` | `detect(root, *, follow_symlinks=False)` | scan a corpus and categorize files by type |
| `extract.py` | `extract(paths, cache_root=None)`, `collect_files(target, ...)` | run AST and semantic extraction into flat node/edge dicts |
| `build.py` | `build_from_json(extraction, *, directed=False)`, `build(extractions, *, directed=False)` | assemble a NetworkX graph from extraction payloads |
| `cluster.py` | `cluster(G)`, `score_all(G, communities)` | compute community assignments and cohesion scores |
| `analyze.py` | `god_nodes(G)`, `surprising_connections(G, ...)`, `suggest_questions(G, ...)` | derive graph-level summaries and navigation hints |
| `report.py` | `generate(...)` | render `GRAPH_REPORT.md` |
| `export.py` | `to_json(...)`, `to_html(...)`, `to_obsidian(...)` | write graph outputs for tools and humans |
| `serve.py` | `python -m tracely360_lite.serve <graph.json>` | expose `graph.json` over MCP stdio |
| `watch.py` | watch/update helpers | incremental graph rebuilds |
| `ingest.py` | URL and file ingestion helpers | pull new corpus material into the graph |
| `security.py` | validation helpers | guard URL fetches, graph paths, and rendered labels |
| `validate.py` | `validate_extraction(data)` | schema validation for extraction payloads |

## Extraction layers

Code extraction is layered so deterministic structure lands first and optional enrichment lands later:

1. Structural AST pass: files, classes, functions, methods, imports, calls, and language-specific constructs.
2. Python rationale pass: module/function/class docstrings plus `# NOTE:` / `# WHY:` style comments.
3. Endpoint pass: deterministic route discovery that emits `endpoint` nodes and `exposes_endpoint` edges.
4. Cross-file resolution: unresolved calls are stored as `raw_calls` and resolved after per-file extraction where supported.

## Endpoint extraction

Endpoint extraction runs as a post-AST pass inside `extract.py` and uses framework-specific walkers in `endpoints.py`.

Supported frameworks:

- Python: Flask, FastAPI, Django URL patterns
- JS/TS: Express, NestJS, Next.js file routes
- Java: Spring MVC annotations
- PHP: Laravel routes and grouped routes
- Ruby: Rails routes and namespaces
- Go: Gin, Echo, Chi router calls and grouped routes
- C#: ASP.NET controller attributes and minimal APIs

Endpoint nodes use `file_type: "endpoint"` and carry `method`, `path`, and `framework` fields. Handler links are represented as `exposes_endpoint` edges.

## Extraction schema

Every extractor returns a flat payload shaped like this:

```json
{
  "nodes": [
    {
      "id": "unique_string",
      "label": "human name",
      "file_type": "code|document|paper|image|rationale|endpoint",
      "source_file": "path",
      "source_location": "L42"
    }
  ],
  "edges": [
    {
      "source": "id_a",
      "target": "id_b",
      "relation": "calls|imports|exposes_endpoint|...",
      "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"
    }
  ],
  "raw_calls": []
}
```

Representative endpoint node:

```json
{
  "id": "users_endpoint_get__api_users",
  "label": "GET /api/users",
  "file_type": "endpoint",
  "method": "GET",
  "path": "/api/users",
  "framework": "spring",
  "source_file": "controllers/UserController.java",
  "source_location": "L14"
}
```

`validate.py` returns a list of schema errors; an empty list means the extraction payload is valid.

## Confidence model

| Label | Meaning |
|-------|---------|
| `EXTRACTED` | Directly proven by the source or parser |
| `INFERRED` | Reasonable structural or semantic inference with supporting context |
| `AMBIGUOUS` | Uncertain edge kept visible for review |

## Adding a new language or framework

For a new language extractor:

1. Add `extract_<lang>(path: Path) -> dict` in `extract.py` or a dedicated helper module.
2. Register the suffix in `extract()` dispatch and detection/watch extension sets.
3. Add any required tree-sitter package to `pyproject.toml`.
4. Add focused fixtures and tests under `tests/fixtures/` and the relevant test module.

For a new endpoint framework:

1. Add a walker to `endpoints.py`.
2. Reuse the `endpoint` node shape and `exposes_endpoint` edge relation.
3. Add fixture coverage plus one end-to-end pipeline assertion in `tests/test_endpoints.py`.

## Security boundaries

Before data reaches the graph or renderer, `security.py` enforces:

- URL validation and safe fetch wrappers for explicit network ingestion
- graph path validation for MCP server startup
- label sanitization before vis.js HTML rendering and MCP text output
- size caps and redirect validation on downloaded remote content

See `SECURITY.md` for the full threat model.

## Testing

Run the full suite with:

```bash
pytest tests/ -q
```

The suite includes per-module unit tests, endpoint fixtures across multiple frameworks, and an end-to-end pipeline test that verifies endpoint nodes survive build, cluster, report, and HTML export.
