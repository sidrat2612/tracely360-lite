# tracely360-lite


Turn any folder of code, docs, papers, images, or videos into a queryable knowledge graph. Type `/tracely360-lite` in your AI coding assistant — it reads your files, builds a graph, and gives you back structure you didn't know was there. Understand a codebase faster. Find the "why" behind architectural decisions.

71.5× fewer tokens per query vs reading the raw files, persistent across sessions, honest about what it found vs guessed.

## Highlights

- **Deterministic AST extraction** — 25 languages via tree-sitter (Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir, Objective-C, Julia, Verilog, SystemVerilog, Vue, Svelte, Dart)
- **API endpoint discovery** — Flask, FastAPI, Django, Express, NestJS, Next.js, Spring, Laravel, Rails, Gin, Echo, Chi, ASP.NET
- **Multimodal** — code, markdown, PDFs, images, screenshots, diagrams, whiteboard photos, video and audio (transcribed via faster-whisper with domain-aware prompts)
- **Leiden community detection** — topology-based clustering, no embeddings, no LLM calls
- **Multiple exports** — interactive HTML (vis.js), persistent JSON, Obsidian wiki, SVG, markdown report
- **MCP server** — expose the graph over stdio for Claude, Codex, and other agents
- **Per-file caching** — re-runs only process changed files (SHA256-based)
- **Git hooks** — auto-rebuild on commit/checkout

## Install

```bash
pip install tracely360-lite
tracely360-lite install
```

Optional extras:

```bash
pip install "tracely360-lite[mcp]"      # MCP stdio server
pip install "tracely360-lite[neo4j]"    # Neo4j push
pip install "tracely360-lite[pdf]"      # PDF extraction
pip install "tracely360-lite[video]"    # Video/audio transcription
pip install "tracely360-lite[watch]"    # File watcher
pip install "tracely360-lite[svg]"      # Static SVG export
pip install "tracely360-lite[leiden]"   # Leiden clustering (Python <3.13)
pip install "tracely360-lite[office]"   # Word/Excel conversion
pip install "tracely360-lite[all]"      # Everything
```

## Quick start

### Skill mode (recommended)

Type `/tracely360-lite .` in Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, or Google Antigravity.

### CLI mode

```bash
tracely360-lite --analyze /path/to/repo --output ./tracely360-lite-out
```

### Watch mode

```bash
tracely360-lite watch
```

Auto-rebuilds the AST graph on file changes. No LLM required.

### MCP server

```bash
python -m tracely360_lite.serve
```

Exposes the graph over stdio. Tools: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`.

## Outputs

All results land in `tracely360-lite-out/`:

| File | Description |
|------|-------------|
| `GRAPH_REPORT.md` | One-page audit: god nodes, communities, surprising connections, API endpoints, knowledge gaps |
| `graph.json` | Persistent queryable graph (node-link format with community assignments) |
| `graph.html` | Interactive vis.js visualization with search, filtering, and node inspection |
| `wiki/` | Obsidian-compatible markdown vault with bidirectional wikilinks |
| `cache/` | Per-file extraction cache (SHA256-keyed) |

## Supported platforms

| Platform | Install command |
|----------|----------------|
| Claude Code | `tracely360-lite claude install` |
| Codex | `tracely360-lite codex install` |
| OpenCode | `tracely360-lite opencode install` |
| Aider | `tracely360-lite aider install` |
| Cursor | `tracely360-lite cursor install` |
| VS Code Copilot Chat | `tracely360-lite vscode install` |
| GitHub Copilot CLI | `tracely360-lite install --platform copilot` |
| OpenClaw | `tracely360-lite claw install` |
| Factory Droid | `tracely360-lite droid install` |
| Trae | `tracely360-lite trae install` |
| Gemini CLI | `tracely360-lite gemini install` |
| Hermes | `tracely360-lite hermes install` |
| Kiro | `tracely360-lite kiro install` |
| Google Antigravity | `tracely360-lite antigravity install` |

## Git hooks

```bash
tracely360-lite hook install    # post-commit + post-checkout
tracely360-lite hook uninstall
```

Rebuilds the AST-only graph after every commit. Works with Husky and custom `core.hooksPath`.

## API endpoint extraction

Static analysis only — no code execution, no port probing. Detects route decorators/registrations in:

- **Python**: Flask (`@app.route`), FastAPI (`@app.get`), Django (`urlpatterns`)
- **JavaScript/TypeScript**: Express (`app.get`), NestJS (`@Get()`), Next.js API routes
- **Java**: Spring (`@GetMapping`, `@RequestMapping`)
- **PHP**: Laravel (`Route::get`)
- **Ruby**: Rails (`resources`, `get`, `post` in routes.rb)
- **Go**: Gin, Echo, Chi (`r.GET`, `e.GET`, `r.Get`)
- **C#**: ASP.NET (`[HttpGet]`, `MapGet`)

Detected routes appear as `endpoint` nodes in the graph and in the API Endpoints section of the report.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRACELY360LITE_WHISPER_PROMPT` | *(derived from corpus)* | Override faster-whisper prompt |
| `TRACELY360LITE_WHISPER_MODEL` | `base` | Whisper model name |

Legacy names `GRAPHIFY_WHISPER_PROMPT` and `GRAPHIFY_WHISPER_MODEL` are still supported.

## How it works

```
detect() → extract() → build_from_json() → cluster() + score_all()
  → god_nodes() / surprising_connections() / suggest_questions()
  → generate() → to_json() / to_html() / to_wiki()
```

1. **Detect** — scan corpus, classify files (code, document, paper, image, video)
2. **Extract** — two-pass AST extraction: per-file structure, then cross-file import resolution. Endpoint pass discovers API routes.
3. **Build** — assemble NetworkX graph from flat node/edge payloads
4. **Cluster** — Leiden community detection (topology-based, no embeddings)
5. **Analyze** — god nodes, surprising connections, knowledge gaps
6. **Report** — render `GRAPH_REPORT.md` with full audit trail
7. **Export** — interactive HTML, persistent JSON, Obsidian wiki

## Confidence model

Every edge carries a confidence level:

| Level | Meaning |
|-------|---------|
| `EXTRACTED` | Directly proven by source code or parser |
| `INFERRED` | Reasonable structural/semantic inference |
| `AMBIGUOUS` | Uncertain — flagged for review |

## Team workflow

Commit `tracely360-lite-out/` to git. The graph, report, and wiki are plain text and diff cleanly. Use `.tracely360liteignore` (same syntax as `.gitignore`) to exclude files from extraction.

Recommended `.gitignore` additions:

```gitignore
tracely360-lite-out/cache/
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
