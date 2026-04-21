# tracely360-lite

[![CI](https://github.com/sidrat2612/tracely360-lite/actions/workflows/ci.yml/badge.svg?branch=v4)](https://github.com/sidrat2612/tracely360-lite/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tracely360-lite)](https://pypi.org/project/tracely360-lite/)
[![Downloads](https://static.pepy.tech/badge/tracely360-lite)](https://pepy.tech/project/tracely360-lite)
[![Sponsor](https://img.shields.io/badge/sponsor-sidrat2612-ea4aaa?logo=github-sponsors)](https://github.com/sponsors/sidrat2612)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Safi%20Shamsi-0077B5?logo=linkedin)](https://www.linkedin.com/in/safi-shamsi)

**An AI coding assistant skill.** Type `/tracely360-lite` in Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, or Google Antigravity - it reads your files, builds a knowledge graph, and gives you back structure you didn't know was there. Understand a codebase faster. Find the "why" behind architectural decisions.

Fully multimodal. Drop in code, PDFs, markdown, screenshots, diagrams, whiteboard photos, images in other languages, or video and audio files - tracely360-lite extracts concepts and relationships from all of it and connects them into one graph. Videos are transcribed with Whisper using a domain-aware prompt derived from your corpus. 25 languages are supported via tree-sitter AST (Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir, Objective-C, Julia, Verilog, SystemVerilog, Vue, Svelte, Dart), and the deterministic code pass also extracts API endpoints across Flask/FastAPI/Django, Express/NestJS/Next.js, Spring, Laravel, Rails, Gin/Echo/Chi, and ASP.NET.

> Andrej Karpathy keeps a `/raw` folder where he drops papers, tweets, screenshots, and notes. tracely360-lite is the answer to that problem - 71.5x fewer tokens per query vs reading the raw files, persistent across sessions, honest about what it found vs guessed.

```
/tracely360-lite .                        # works on any folder - your codebase, notes, papers, anything
```

```
tracely360-lite-out/
├── graph.html       interactive graph - open in any browser, click nodes, search, filter by community, inspect endpoint nodes
├── GRAPH_REPORT.md  god nodes, surprising connections, API endpoints, suggested questions
├── graph.json       persistent graph - query weeks later without re-reading
└── cache/           SHA256 cache - re-runs only process changed files
```

Add a `.tracely360liteignore` file to exclude folders you don't want in the graph:

```
# .tracely360liteignore
vendor/
node_modules/
dist/
*.generated.py
```

Same syntax as `.gitignore`. You can keep a single `.tracely360liteignore` at your repo root — patterns work correctly even when tracely360-lite is run on a subfolder.

## How it works

tracely360-lite runs in three passes. First, a deterministic AST pass extracts structure from code files (classes, functions, imports, call graphs, docstrings, rationale comments, and API routes) with no LLM needed. Second, video and audio files are transcribed locally with faster-whisper using a domain-aware prompt derived from corpus god nodes — transcripts are cached so re-runs are instant. Third, Claude subagents run in parallel over docs, papers, images, and transcripts to extract concepts, relationships, and design rationale. The results are merged into a NetworkX graph, clustered with Leiden community detection, and exported as interactive HTML, queryable JSON, and a plain-language audit report.

**Clustering is graph-topology-based — no embeddings.** Leiden finds communities by edge density. The semantic similarity edges that Claude extracts (`semantically_similar_to`, marked INFERRED) are already in the graph, so they influence community detection directly. The graph structure is the similarity signal — no separate embedding step or vector database needed.

Every relationship is tagged `EXTRACTED` (found directly in source), `INFERRED` (reasonable inference, with a confidence score), or `AMBIGUOUS` (flagged for review). You always know what was found vs guessed.

### API endpoint extraction

The deterministic AST pass adds `endpoint` nodes and `exposes_endpoint` edges for common web frameworks. Today that includes:

- Python: Flask, FastAPI, Django URL patterns
- JS/TS: Express, NestJS, Next.js file routes
- Java: Spring `@RequestMapping`, `@GetMapping`, `@PostMapping`, and related annotations
- PHP: Laravel `Route::get`, `Route::group`, `Route::resource`
- Ruby: Rails `get`, `post`, `resources`, `namespace`
- Go: Gin, Echo, Chi router calls and grouped routes
- C#: ASP.NET controller attributes and minimal API `MapGet`/`MapPost` style routes

In `graph.html`, endpoint nodes are highlighted as star nodes. In `GRAPH_REPORT.md`, they appear in a dedicated `API Endpoints` section.

## Install

**Requires:** Python 3.10+ and one of: [Claude Code](https://claude.ai/code), [Codex](https://openai.com/codex), [OpenCode](https://opencode.ai), [Cursor](https://cursor.com), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli), [VS Code Copilot Chat](https://code.visualstudio.com/docs/copilot/overview), [Aider](https://aider.chat), [OpenClaw](https://openclaw.ai), [Factory Droid](https://factory.ai), [Trae](https://trae.ai), [Kiro](https://kiro.dev), Hermes, or [Google Antigravity](https://antigravity.google)

```bash
pip install tracely360-lite && tracely360-lite install
# or with pipx (keeps the CLI isolated from your project environments)
pipx install tracely360-lite && tracely360-lite install
```

> **Official package:** The PyPI package is named `tracely360-lite` (install with `pip install tracely360-lite`). Other packages named `tracely360-lite*` on PyPI are not affiliated with this project. The only official repository is [sidrat2612/tracely360-lite](https://github.com/sidrat2612/tracely360-lite). The CLI and skill command are still `tracely360-lite`.

> **`tracely360-lite: command not found`?** On Windows, pip user scripts land in `%APPDATA%\Python\PythonXY\Scripts` — add that to your PATH or use `python -m tracely360_lite` instead. On macOS with pipx, run `pipx ensurepath` then restart your terminal.

### Platform support

| Platform | Install command |
|----------|----------------|
| Claude Code (Linux/Mac) | `tracely360-lite install` |
| Claude Code (Windows) | `tracely360-lite install` (auto-detected) or `tracely360-lite install --platform windows` |
| Codex | `tracely360-lite install --platform codex` |
| OpenCode | `tracely360-lite install --platform opencode` |
| GitHub Copilot CLI | `tracely360-lite install --platform copilot` |
| VS Code Copilot Chat | `tracely360-lite vscode install` |
| Aider | `tracely360-lite install --platform aider` |
| OpenClaw | `tracely360-lite install --platform claw` |
| Factory Droid | `tracely360-lite install --platform droid` |
| Trae | `tracely360-lite install --platform trae` |
| Trae CN | `tracely360-lite install --platform trae-cn` |
| Gemini CLI | `tracely360-lite install --platform gemini` |
| Hermes | `tracely360-lite install --platform hermes` |
| Kiro IDE/CLI | `tracely360-lite kiro install` |
| Cursor | `tracely360-lite cursor install` |
| Google Antigravity | `tracely360-lite antigravity install` |

Codex users also need `multi_agent = true` under `[features]` in `~/.codex/config.toml` for parallel extraction. Factory Droid uses the `Task` tool for parallel subagent dispatch. OpenClaw and Aider use sequential extraction (parallel agent support is still early on those platforms). Trae uses the Agent tool for parallel subagent dispatch and does **not** support PreToolUse hooks — AGENTS.md is the always-on mechanism. Codex supports PreToolUse hooks — `tracely360-lite codex install` installs one in `.codex/hooks.json` in addition to writing AGENTS.md.

Then open your AI coding assistant and type:

```
/tracely360-lite .
```

Note: Codex uses `$` instead of `/` for skill calling, so type `$tracely360-lite .` instead.

### Make your assistant always use the graph (recommended)

After building a graph, run this once in your project:

| Platform | Command |
|----------|---------|
| Claude Code | `tracely360-lite claude install` |
| Codex | `tracely360-lite codex install` |
| OpenCode | `tracely360-lite opencode install` |
| GitHub Copilot CLI | `tracely360-lite copilot install` |
| VS Code Copilot Chat | `tracely360-lite vscode install` |
| Aider | `tracely360-lite aider install` |
| OpenClaw | `tracely360-lite claw install` |
| Factory Droid | `tracely360-lite droid install` |
| Trae | `tracely360-lite trae install` |
| Trae CN | `tracely360-lite trae-cn install` |
| Cursor | `tracely360-lite cursor install` |
| Gemini CLI | `tracely360-lite gemini install` |
| Hermes | `tracely360-lite hermes install` |
| Kiro IDE/CLI | `tracely360-lite kiro install` |
| Google Antigravity | `tracely360-lite antigravity install` |

**Claude Code** does two things: writes a `CLAUDE.md` section telling Claude to read `tracely360-lite-out/GRAPH_REPORT.md` before answering architecture questions, and installs a **PreToolUse hook** (`settings.json`) that fires before every Glob and Grep call. If a knowledge graph exists, Claude sees: _"tracely360-lite: Knowledge graph exists. Read GRAPH_REPORT.md for god nodes and community structure before searching raw files."_ — so Claude navigates via the graph instead of grepping through every file.

**Codex** writes to `AGENTS.md` and also installs a **PreToolUse hook** in `.codex/hooks.json` that fires before every Bash tool call — same always-on mechanism as Claude Code.

**OpenCode** writes to `AGENTS.md` and also installs a **`tool.execute.before` plugin** (`.opencode/plugins/tracely360-lite.js` + `opencode.json` registration) that fires before bash tool calls and injects the graph reminder into tool output when the graph exists.

**Cursor** writes `.cursor/rules/tracely360-lite.mdc` with `alwaysApply: true` — Cursor includes it in every conversation automatically, no hook needed.

**Gemini CLI** copies the skill to `~/.gemini/skills/tracely360-lite/SKILL.md`, writes a `GEMINI.md` section, and installs a `BeforeTool` hook in `.gemini/settings.json` that fires before file-read tool calls — same always-on mechanism as Claude Code.

**Aider, OpenClaw, Factory Droid, Trae, and Hermes** write the same rules to `AGENTS.md` in your project root and copy the skill to the platform's global skill directory. These platforms don't support tool hooks, so AGENTS.md is the always-on mechanism.

**Kiro IDE/CLI** writes the skill to `.kiro/skills/tracely360-lite/SKILL.md` (invoked via `/tracely360-lite`) and a steering file to `.kiro/steering/tracely360-lite.md` with `inclusion: always` — Kiro injects this into every conversation automatically, no hook needed.

**Google Antigravity** writes `.agent/rules/tracely360-lite.md` (always-on rules) and `.agent/workflows/tracely360-lite.md` (registers `/tracely360-lite` as a slash command). No hook equivalent exists in Antigravity — rules are the always-on mechanism.

**GitHub Copilot CLI** copies the skill to `~/.copilot/skills/tracely360-lite/SKILL.md`. Run `tracely360-lite copilot install` to set it up.

**VS Code Copilot Chat** installs a Python-only skill (works on Windows PowerShell and macOS/Linux alike) and writes `.github/copilot-instructions.md` in your project root — VS Code reads this automatically every session, making graph context always-on without any hook mechanism. Run `tracely360-lite vscode install`. Note: this configures the chat panel in VS Code, not the Copilot CLI terminal tool.

Uninstall with the matching uninstall command (e.g. `tracely360-lite claude uninstall`).

**Always-on vs explicit trigger — what's the difference?**

The always-on hook surfaces `GRAPH_REPORT.md` — a one-page summary of god nodes, communities, and surprising connections. Your assistant reads this before searching files, so it navigates by structure instead of keyword matching. That covers most everyday questions.

`/tracely360-lite query`, `/tracely360-lite path`, and `/tracely360-lite explain` go deeper: they traverse the raw `graph.json` hop by hop, trace exact paths between nodes, and surface edge-level detail (relation type, confidence score, source location). Use them when you want a specific question answered from the graph rather than a general orientation.

Think of it this way: the always-on hook gives your assistant a map. The `/tracely360-lite` commands let it navigate the map precisely.

### Team workflows

`tracely360-lite-out/` is designed to be committed to git so every teammate starts with a fresh map.

**Recommended `.gitignore` additions:**
```
# commit graph outputs, ignore the extraction cache
tracely360-lite-out/cache/
```

**Shared setup:**
1. One person runs `/tracely360-lite .` to build the initial graph and commits `tracely360-lite-out/`.
2. Everyone else pulls — their assistant reads `GRAPH_REPORT.md` immediately with no extra steps.
3. Install the post-commit hook (`tracely360-lite hook install`) so the graph rebuilds automatically after code changes — no LLM calls needed for code-only updates.
4. For doc/paper changes, whoever edits the files runs `/tracely360-lite --update` to refresh semantic nodes.

**Excluding paths** — create `.tracely360liteignore` in your project root (same syntax as `.gitignore`). Files matching those patterns are skipped during detection and extraction.

## Using `graph.json` with an LLM

`graph.json` is not meant to be pasted into a prompt all at once. The useful
workflow is:

1. Start with `tracely360-lite-out/GRAPH_REPORT.md` for the high-level overview.
2. Use `tracely360-lite query` to pull a smaller subgraph for the specific question
   you want to answer.
3. Give that focused output to your assistant instead of dumping the full raw
   corpus.

For example, after running tracely360-lite on a project:

```bash
tracely360-lite query "show the auth flow" --graph tracely360-lite-out/graph.json
tracely360-lite query "what connects DigestAuth to Response?" --graph tracely360-lite-out/graph.json
```

The output includes node labels, edge types, confidence tags, source files, and
source locations. That makes it a good intermediate context block for an LLM:

```text
Use this graph query output to answer the question. Prefer the graph structure
over guessing, and cite the source files when possible.
```

If your assistant supports tool calling or MCP, use the graph directly instead
of pasting text. tracely360-lite can expose `graph.json` as an MCP server:

```bash
python -m tracely360_lite.serve tracely360-lite-out/graph.json
```

That gives the assistant structured graph access for repeated queries such as
`query_graph`, `get_node`, `get_neighbors`, and `shortest_path`.

> **WSL / Linux note:** Ubuntu ships `python3`, not `python`. Install into a project venv to avoid PEP 668 conflicts, and use the full venv path in your `.mcp.json`:
> ```bash
> python3 -m venv .venv && .venv/bin/pip install "tracely360-lite[mcp]"
> ```
> ```json
> { "mcpServers": { "tracely360-lite": { "type": "stdio", "command": ".venv/bin/python3", "args": ["-m", "tracely360_lite.serve", "tracely360-lite-out/graph.json"] } } }
> ```
> The package name is `tracely360-lite`, while the Python module path is `tracely360_lite`.

<details>
<summary>Manual install (curl)</summary>

```bash
mkdir -p ~/.claude/skills/tracely360-lite
curl -fsSL https://raw.githubusercontent.com/sidrat2612/tracely360-lite/v4/tracely360_lite/skill.md \
  > ~/.claude/skills/tracely360-lite/SKILL.md
```

Add to `~/.claude/CLAUDE.md`:

```
- **tracely360-lite** (`~/.claude/skills/tracely360-lite/SKILL.md`) - any input to knowledge graph. Trigger: `/tracely360-lite`
When the user types `/tracely360-lite`, invoke the Skill tool with `skill: "tracely360-lite"` before doing anything else.
```

</details>

## Usage

```
/tracely360-lite                          # run on current directory
/tracely360-lite ./raw                    # run on a specific folder
/tracely360-lite ./raw --mode deep        # more aggressive INFERRED edge extraction
/tracely360-lite ./raw --update           # re-extract only changed files, merge into existing graph
/tracely360-lite ./raw --directed          # build directed graph (preserves edge direction: source→target)
/tracely360-lite ./raw --cluster-only     # rerun clustering on existing graph, no re-extraction
/tracely360-lite ./raw --no-viz           # skip HTML, just produce report + JSON
/tracely360-lite ./raw --obsidian                          # also generate Obsidian vault (opt-in)
/tracely360-lite ./raw --obsidian --obsidian-dir ~/vaults/myproject  # write vault to a specific directory

/tracely360-lite add https://arxiv.org/abs/1706.03762        # fetch a paper, save, update graph
/tracely360-lite add https://x.com/karpathy/status/...       # fetch a tweet
/tracely360-lite add <video-url>                              # download audio, transcribe, add to graph
/tracely360-lite add https://... --author "Name"             # tag the original author
/tracely360-lite add https://... --contributor "Name"        # tag who added it to the corpus

/tracely360-lite query "what connects attention to the optimizer?"
/tracely360-lite query "what connects attention to the optimizer?" --dfs   # trace a specific path
/tracely360-lite query "what connects attention to the optimizer?" --budget 1500  # cap at N tokens
/tracely360-lite path "DigestAuth" "Response"
/tracely360-lite explain "SwinTransformer"

/tracely360-lite ./raw --watch            # auto-sync graph as files change (code: instant, docs: notifies you)
/tracely360-lite ./raw --wiki             # build agent-crawlable wiki (index.md + article per community)
/tracely360-lite ./raw --svg              # export graph.svg
/tracely360-lite ./raw --graphml          # export graph.graphml (Gephi, yEd)
/tracely360-lite ./raw --neo4j            # generate cypher.txt for Neo4j
/tracely360-lite ./raw --neo4j-push bolt://localhost:7687    # push directly to a running Neo4j instance
/tracely360-lite ./raw --mcp              # start MCP stdio server

# git hooks - platform-agnostic, rebuild graph on commit and branch switch
tracely360-lite hook install
tracely360-lite hook uninstall
tracely360-lite hook status

# always-on assistant instructions - platform-specific
tracely360-lite claude install            # CLAUDE.md + PreToolUse hook (Claude Code)
tracely360-lite claude uninstall
tracely360-lite codex install             # AGENTS.md + PreToolUse hook in .codex/hooks.json (Codex)
tracely360-lite opencode install          # AGENTS.md + tool.execute.before plugin (OpenCode)
tracely360-lite cursor install            # .cursor/rules/tracely360-lite.mdc (Cursor)
tracely360-lite cursor uninstall
tracely360-lite gemini install            # GEMINI.md + BeforeTool hook (Gemini CLI)
tracely360-lite gemini uninstall
tracely360-lite copilot install           # skill file (GitHub Copilot CLI)
tracely360-lite copilot uninstall
tracely360-lite aider install             # AGENTS.md (Aider)
tracely360-lite aider uninstall
tracely360-lite claw install              # AGENTS.md (OpenClaw)
tracely360-lite droid install             # AGENTS.md (Factory Droid)
tracely360-lite trae install              # AGENTS.md (Trae)
tracely360-lite trae uninstall
tracely360-lite trae-cn install           # AGENTS.md (Trae CN)
tracely360-lite trae-cn uninstall
tracely360-lite hermes install             # AGENTS.md + ~/.hermes/skills/ (Hermes)
tracely360-lite hermes uninstall
tracely360-lite kiro install               # .kiro/skills/ + .kiro/steering/tracely360-lite.md (Kiro IDE/CLI)
tracely360-lite kiro uninstall
tracely360-lite antigravity install       # .agent/rules + .agent/workflows (Google Antigravity)
tracely360-lite antigravity uninstall

# query and navigate the graph directly from the terminal (no AI assistant needed)
tracely360-lite query "what connects attention to the optimizer?"
tracely360-lite query "show the auth flow" --dfs
tracely360-lite query "what is CfgNode?" --budget 500
tracely360-lite query "..." --graph path/to/graph.json
tracely360-lite path "DigestAuth" "Response"       # shortest path between two nodes
tracely360-lite explain "SwinTransformer"           # plain-language explanation of a node

# add content and update the graph from the terminal
tracely360-lite add https://arxiv.org/abs/1706.03762          # fetch paper, save to ./raw, update graph
tracely360-lite add https://... --author "Name" --contributor "Name"

# incremental update and maintenance
tracely360-lite watch ./src                         # auto-rebuild on code changes
tracely360-lite update ./src                        # re-extract code files, no LLM needed
tracely360-lite cluster-only ./my-project           # rerun clustering on existing graph.json
```

Works with any mix of file types:

| Type | Extensions | Extraction |
|------|-----------|------------|
| Code | `.py .ts .js .jsx .tsx .mjs .go .rs .java .c .cpp .rb .cs .kt .scala .php .swift .lua .zig .ps1 .ex .exs .m .mm .jl .vue .svelte` | AST via tree-sitter + call-graph (cross-file for all languages) + docstring/comment rationale |
| Docs | `.md .mdx .html .txt .rst` | Concepts + relationships + design rationale via Claude |
| Office | `.docx .xlsx` | Converted to markdown then extracted via Claude (requires `pip install tracely360-lite[office]`) |
| Papers | `.pdf` | Citation mining + concept extraction |
| Images | `.png .jpg .webp .gif` | Claude vision - screenshots, diagrams, any language |
| Video / Audio | `.mp4 .mov .mkv .webm .avi .m4v .mp3 .wav .m4a .ogg` | Transcribed locally with faster-whisper, transcript fed into Claude extraction (requires `pip install tracely360-lite[video]`) |
| YouTube / URLs | any video URL | Audio downloaded via yt-dlp, then same Whisper pipeline (requires `pip install tracely360-lite[video]`) |

## Video and audio corpus

Drop video or audio files into your corpus folder alongside your code and docs — tracely360-lite picks them up automatically:

```bash
pip install 'tracely360-lite[video]'   # one-time setup
/tracely360-lite ./my-corpus            # transcribes any video/audio files it finds
```

Add a YouTube video (or any public video URL) directly:

```bash
/tracely360-lite add <video-url>
```

yt-dlp downloads audio-only (fast, small), Whisper transcribes it locally, and the transcript is fed into the same extraction pipeline as your other docs. Transcripts are cached in `tracely360-lite-out/transcripts/` so re-runs skip already-transcribed files.

For better accuracy on technical content, use a larger model:

```bash
/tracely360-lite ./my-corpus --whisper-model medium
```

Audio never leaves your machine. All transcription runs locally.

## What you get

**God nodes** - highest-degree concepts (what everything connects through)

**Surprising connections** - ranked by composite score. Code-paper edges rank higher than code-code. Each result includes a plain-English why.

**Suggested questions** - 4-5 questions the graph is uniquely positioned to answer

**The "why"** - docstrings, inline comments (`# NOTE:`, `# IMPORTANT:`, `# HACK:`, `# WHY:`), and design rationale from docs are extracted as `rationale_for` nodes. Not just what the code does - why it was written that way.

**Confidence scores** - every INFERRED edge has a `confidence_score` (0.0-1.0). You know not just what was guessed but how confident the model was. EXTRACTED edges are always 1.0.

**Semantic similarity edges** - cross-file conceptual links with no structural connection. Two functions solving the same problem without calling each other, a class in code and a concept in a paper describing the same algorithm.

**Hyperedges** - group relationships connecting 3+ nodes that pairwise edges can't express. All classes implementing a shared protocol, all functions in an auth flow, all concepts from a paper section forming one idea.

**Token benchmark** - printed automatically after every run. On a mixed corpus (Karpathy repos + papers + images): **71.5x** fewer tokens per query vs reading raw files. The first run extracts and builds the graph (this costs tokens). Every subsequent query reads the compact graph instead of raw files — that's where the savings compound. The SHA256 cache means re-runs only re-process changed files.

**Auto-sync** (`--watch`) - run in a background terminal and the graph updates itself as your codebase changes. Code file saves trigger an instant rebuild (AST only, no LLM). Doc/image changes notify you to run `--update` for the LLM re-pass.

**Git hooks** (`tracely360-lite hook install`) - installs post-commit and post-checkout hooks. Graph rebuilds automatically after every commit and every branch switch. If a rebuild fails, the hook exits with a non-zero code so git surfaces the error instead of silently continuing. No background process needed.

**Wiki** (`--wiki`) - Wikipedia-style markdown articles per community and god node, with an `index.md` entry point. Point any agent at `index.md` and it can navigate the knowledge base by reading files instead of parsing JSON.

## Worked examples

| Corpus | Files | Reduction | Output |
|--------|-------|-----------|--------|
| Karpathy repos + 5 papers + 4 images | 52 | **71.5x** | [`worked/karpathy-repos/`](worked/karpathy-repos/) |
| tracely360-lite source + Transformer paper | 4 | **5.4x** | [`worked/mixed-corpus/`](worked/mixed-corpus/) |
| httpx (synthetic Python library) | 6 | ~1x | [`worked/httpx/`](worked/httpx/) |

Token reduction scales with corpus size. 6 files fits in a context window anyway, so graph value there is structural clarity, not compression. At 52 files (code + papers + images) you get 71x+. Each `worked/` folder has the raw input files and the actual output (`GRAPH_REPORT.md`, `graph.json`) so you can run it yourself and verify the numbers.

## Privacy

tracely360-lite sends file contents to your AI coding assistant's underlying model API for semantic extraction of docs, papers, and images — Anthropic (Claude Code), OpenAI (Codex), or whichever provider your platform uses. Code files are processed locally via tree-sitter AST — no file contents leave your machine for code. Video and audio files are transcribed locally with faster-whisper — audio never leaves your machine. No telemetry, usage tracking, or analytics of any kind. The only network calls are to your platform's model API during extraction, using your own API key.

## Tech stack

NetworkX + Leiden (graspologic) + tree-sitter + vis.js. Semantic extraction via Claude (Claude Code), GPT-4 (Codex), or whichever model your platform runs. Video transcription via faster-whisper + yt-dlp (optional, `pip install tracely360-lite[video]`). No Neo4j required, no server, runs entirely locally.

## Built on tracely360-lite — Penpax

[**Penpax**](https://sidrat2612.github.io/penpax.ai) is the enterprise layer on top of tracely360-lite. Where tracely360-lite turns a folder of files into a knowledge graph, Penpax applies the same graph to your entire working life — continuously.

| | tracely360-lite | Penpax |
|---|---|---|
| Input | A folder of files | Browser history, meetings, emails, files, code — everything |
| Runs | On demand | Continuously in the background |
| Scope | A project | Your entire working life |
| Query | CLI / MCP / AI skill | Natural language, always on |
| Privacy | Local by default | Fully on-device, no cloud |

Built for lawyers, consultants, executives, doctors, researchers — anyone whose work lives across hundreds of conversations and documents they can never fully reconstruct.

**Free trial launching soon.** [Join the waitlist →](https://sidrat2612.github.io/penpax.ai)

## What we are building next

tracely360-lite is the graph layer. Penpax is the always-on layer on top of it — an on-device digital twin that connects your meetings, browser history, files, emails, and code into one continuously updating knowledge graph. No cloud, no training on your data. [Join the waitlist.](https://sidrat2612.github.io/penpax.ai)

## Star history

[![Star History Chart](https://api.star-history.com/svg?repos=sidrat2612/tracely360-lite&type=Date)](https://star-history.com/#sidrat2612/tracely360-lite&Date)

<details>
<summary>Contributing</summary>

**Worked examples** are the most trust-building contribution. Run `/tracely360-lite` on a real corpus, save output to `worked/{slug}/`, write an honest `review.md` evaluating what the graph got right and wrong, submit a PR.

**Extraction bugs** - open an issue with the input file, the cache entry (`tracely360-lite-out/cache/`), and what was missed or invented.

See [ARCHITECTURE.md](ARCHITECTURE.md) for module responsibilities and how to add a language.

</details>
