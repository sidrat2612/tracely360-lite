# Architecture

## Pipeline

```
detect() → extract() → build_from_json() → cluster() + score_all()
  → god_nodes() / surprising_connections() / suggest_questions()
  → generate() → to_json() / to_html() / to_wiki()
```

## Modules

| Module | Entry point | Purpose |
|--------|-------------|---------|
| `detect.py` | `detect(root)`, `classify_file(path)` | Scan corpus, classify files by type (code, document, paper, image, video), respect `.tracely360ignore` |
| `extract.py` | `extract(paths, cache_root)`, `collect_files(target)` | Two-pass AST extraction + cross-file import resolution + endpoint discovery |
| `build.py` | `build_from_json(extraction)`, `build(extractions)` | Assemble NetworkX graph from flat node/edge payloads; deduplication, ID normalization |
| `cluster.py` | `cluster(G)`, `score_all(G, communities)` | Leiden community detection, cohesion scoring, oversized community splitting |
| `analyze.py` | `god_nodes(G)`, `surprising_connections(G, communities)`, `suggest_questions(G, communities, labels)` | Graph-level summaries: most-connected nodes, cross-community edges, navigation hints |
| `report.py` | `generate(...)` | Render `GRAPH_REPORT.md` — corpus check, communities, god nodes, surprises, endpoints, gaps |
| `export.py` | `to_json()`, `to_html()`, `to_svg()`, `to_canvas()` | Multi-format graph export (vis.js HTML, node-link JSON, SVG, canvas) |
| `wiki.py` | `to_wiki(G, communities, output_dir)` | Wikipedia-style markdown vault with bidirectional wikilinks |
| `serve.py` | `serve(graph_path)` | MCP stdio server — 7 tools for agent access to the graph |
| `ingest.py` | `ingest(url, target_dir)` | Fetch URLs (tweets, arXiv, PDFs, images, YouTube, web pages) into tracely360-ready files |
| `transcribe.py` | `transcribe(video_path)`, `transcribe_all(video_files)` | faster-whisper transcription with domain-aware prompts from corpus god nodes |
| `hooks.py` | `install(path)`, `uninstall(path)` | Git post-commit/post-checkout hooks for auto-rebuild |
| `watch.py` | `watch(watch_path, debounce)` | File system watcher — instant AST rebuild on code changes |
| `cache.py` | `load_cached()`, `save_cached()`, `file_hash()` | Per-file SHA256 extraction cache |
| `validate.py` | `validate_extraction(data)`, `assert_valid(data)` | Schema validation for extraction payloads |
| `security.py` | `validate_url()`, `safe_fetch()`, `validate_graph_path()`, `sanitize_label()` | SSRF protection, path traversal prevention, XSS sanitization |
| `benchmark.py` | `run_benchmark(graph_path)` | Measure token reduction: corpus tokens vs query tokens |
| `manifest.py` | *(re-exports from detect.py)* | Backward-compatible manifest API |

## Extraction layers

1. **Structural AST** — files, classes, functions, methods, imports, call graphs via tree-sitter. 25 languages. Each language has a `LanguageConfig` dataclass specifying node types, import handlers, and body detection rules.

2. **Python rationale** — module/function/class docstrings + `# NOTE:` / `# WHY:` style comments. Emits `rationale` nodes.

3. **Endpoint pass** — deterministic route discovery via `endpoints.py`. Static AST analysis only — no code execution or network probing. Supports Flask, FastAPI, Django, Express, NestJS, Next.js, Spring, Laravel, Rails, Gin, Echo, Chi, ASP.NET.

4. **Cross-file resolution** — unresolved call sites (`raw_calls`) stored per-file during pass 1, then resolved against a global label map in a post-pass.

## Node schema

```json
{
  "id": "unique_string",
  "label": "human-readable name",
  "file_type": "code | document | paper | image | rationale | endpoint",
  "source_file": "relative/path",
  "source_location": "L42"
}
```

Endpoint nodes additionally carry `method`, `path`, and `framework` fields.

## Edge schema

```json
{
  "source": "node_id",
  "target": "node_id",
  "relation": "calls | imports | exposes_endpoint | inherits | ...",
  "confidence": "EXTRACTED | INFERRED | AMBIGUOUS",
  "source_file": "relative/path",
  "source_location": "L10"
}
```

## Confidence model

| Level | Meaning |
|-------|---------|
| `EXTRACTED` | Directly proven by source code or parser |
| `INFERRED` | Reasonable structural/semantic inference |
| `AMBIGUOUS` | Uncertain — flagged for human review |

## Graph construction

`build_from_json()` handles three layers of deduplication:

1. **Within-file** — AST produces unique IDs per extraction
2. **Between-files** — NetworkX idempotent node/edge insertion
3. **Semantic merge** — regex-based ID canonicalization for mismatched identifiers

`directed=True` preserves source→target flow via `_src`/`_tgt` edge attributes. Default is undirected for backward compatibility.

## Community detection

Leiden algorithm (graspologic if available, else NetworkX Louvain fallback). Communities indexed by size: 0 = largest. Oversized communities (>25% of graph) are split via recursive pass. DiGraphs are converted to undirected internally. Isolates get their own singleton communities.

## MCP tools

7 tools exposed via `serve.py`:

| Tool | Purpose |
|------|---------|
| `query_graph(question, mode, depth, token_budget)` | BFS/DFS traversal from keyword-scored start nodes |
| `get_node(label)` | Full node details |
| `get_neighbors(label, relation_filter)` | Direct neighbors with edge info |
| `get_community(community_id)` | All nodes in a community |
| `god_nodes(top_n)` | Most connected nodes |
| `graph_stats()` | Node/edge/community summary + confidence breakdown |
| `shortest_path(source, target, max_hops)` | Path finding between concepts |

Communication is stdio only — no network listener.

## File detection

`detect()` classifies files into: CODE, DOCUMENT, PAPER, IMAGE, OFFICE, VIDEO.

Paper detection uses a heuristic (arxiv IDs, DOI, "abstract", citations, `\cite` — threshold: 3+ signals).

Sensitive files (`.pem`, `.key`, `.env`, credentials) and dependency directories (`node_modules`, `venv`, `dist`, `__pycache__`) are always excluded. `.tracely360ignore` supports gitignore syntax for custom exclusions.

## Caching

Per-file extraction cache in `tracely360-out/cache/`. Keyed by SHA256 of file contents + relative path. Markdown files ignore YAML frontmatter changes. Portable across machines via relative paths.

## Report structure

`GRAPH_REPORT.md` sections:

1. Corpus Check — file count, word count, verdict
2. Summary — nodes, edges, communities, confidence breakdown, token cost
3. Community Hubs — wikilinks to per-community pages
4. God Nodes — top 10 most-connected entities
5. Surprising Connections — cross-community edges ranked by surprise score
6. Hyperedges — group relationships
7. Communities — per-community breakdown (label, cohesion, top nodes, cross-community links)
8. Ambiguous Edges — flagged for review
9. Knowledge Gaps — isolated nodes, thin communities, high ambiguity
10. API Endpoints — table of detected routes (method, path, framework, source)
11. Suggested Questions — questions the graph can answer
# Architecture

tracely360 is a local knowledge-graph engine packaged behind a CLI, assistant skills, and an optional MCP stdio server. The code path is deterministic for source files; semantic extraction for docs, papers, images, and transcripts is layered on top.

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

The pipeline passes plain Python dicts and NetworkX graphs between stages. Persistent outputs land under `tracely360-out/`.

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
| `serve.py` | `python -m tracely360.serve <graph.json>` | expose `graph.json` over MCP stdio |
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
