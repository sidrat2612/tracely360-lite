# tracely360


Turn any folder of code, docs, papers, images, or videos into a queryable knowledge graph. Type `/tracely360` in your AI coding assistant — it reads your files, builds a graph, and gives you back structure you didn't know was there. Understand a codebase faster. Find the "why" behind architectural decisions.

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

## Project scope

- Deterministic, local-first analysis. Core graph extraction should stay explainable and reproducible.
- No hosted LLM dependency in the analysis pipeline.
- If you want to propose a large feature or scope change, open an issue before sending a pull request.

## Install

```bash
pip install tracely360
tracely360 install
```

Optional extras:

```bash
pip install "tracely360[mcp]"      # MCP stdio server
pip install "tracely360[neo4j]"    # Neo4j push
pip install "tracely360[pdf]"      # PDF extraction
pip install "tracely360[video]"    # Video/audio transcription
pip install "tracely360[watch]"    # File watcher
pip install "tracely360[svg]"      # Static SVG export
pip install "tracely360[leiden]"   # Leiden clustering (Python <3.13)
pip install "tracely360[office]"   # Word/Excel conversion
pip install "tracely360[all]"      # Everything
```

## Quick start

### Skill mode (recommended)

Type `/tracely360 .` in Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, or Google Antigravity.

### CLI utilities

```bash
tracely360 query "How is AuthController connected to Service?"
tracely360 path "AuthController" "Service"
tracely360 explain "Repository"
```

For full graph builds, use the assistant skill mode above. The direct CLI exposes utilities like `update`, `watch`, `query`, `path`, `explain`, and platform installers.

### Watch mode

```bash
tracely360 watch
```

Auto-rebuilds the AST graph on file changes. No LLM required.

### MCP server

```bash
python -m tracely360.serve
```

Exposes the graph over stdio. Tools: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`.

## Outputs

All results land in `tracely360-out/`:

| File | Description |
|------|-------------|
| `GRAPH_REPORT.md` | One-page audit: god nodes, clusters, surprising connections, API endpoints, knowledge gaps |
| `graph.json` | Persistent queryable graph (node-link format with cluster assignments in the `community` field) |
| `graph.html` | Interactive vis.js visualization with search, filtering, and node inspection |
| `wiki/` | Obsidian-compatible markdown vault with bidirectional wikilinks |
| `cache/` | Per-file extraction cache (SHA256-keyed) |

## Supported platforms

| Platform | Install command |
|----------|----------------|
| Claude Code | `tracely360 claude install` |
| Codex | `tracely360 codex install` |
| OpenCode | `tracely360 opencode install` |
| Aider | `tracely360 aider install` |
| Cursor | `tracely360 cursor install` |
| VS Code Copilot Chat | `tracely360 vscode install` |
| GitHub Copilot CLI | `tracely360 install --platform copilot` |
| OpenClaw | `tracely360 claw install` |
| Factory Droid | `tracely360 droid install` |
| Trae | `tracely360 trae install` |
| Gemini CLI | `tracely360 gemini install` |
| Hermes | `tracely360 hermes install` |
| Kiro | `tracely360 kiro install` |
| Google Antigravity | `tracely360 antigravity install` |

## Git hooks

```bash
tracely360 hook install    # post-commit + post-checkout
tracely360 hook uninstall
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
| `TRACELY360_WHISPER_PROMPT` | *(derived from corpus)* | Override faster-whisper prompt |
| `TRACELY360_WHISPER_MODEL` | `base` | Whisper model name |

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
4. **Cluster** — Leiden graph clustering (topology-based, no embeddings)
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

Commit `tracely360-out/` to git. The graph, report, and wiki are plain text and diff cleanly. Use `.tracely360ignore` (same syntax as `.gitignore`) to exclude files from extraction.

Recommended `.gitignore` additions:

```gitignore
tracely360-out/cache/
```

## Community

- Read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SUPPORT.md](SUPPORT.md), and [SECURITY.md](SECURITY.md).
- Use public GitHub issues and pull requests for bugs, proposals, and design discussion. Keep private contact for security reports or sensitive conduct matters only.
- These community docs are aligned with guidance from [Open Source Guides](https://opensource.guide/).

## License

Apache License 2.0. See [LICENSE](LICENSE).
