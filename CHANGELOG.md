# Changelog

Full release notes: [GitHub Releases](https://github.com/sidrat2612/tracely360-lite/releases)

## Unreleased

## 0.4.32 (2026-10-13)

- Fix: the MCP server, `tracely360 query`/`path`/`explain` and the benchmark now read `graph.json` whose node-link edges are under `edges` (the default in current NetworkX, e.g. 3.7) as well as `links`; one loader, `build.graph_from_node_link`, serves them all
- Docs: remove a stale second copy of this changelog (the pre-0.4.28 version, superseded by the rewritten entries above; it remains in git history)

## 0.4.31 (2026-10-13)

- Add: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `graph_stats` and `shortest_path` as library functions in `tracely360.query`, exported from the package with `graph_diff`; they return plain, JSON-serializable data
- Change: the MCP tools render those functions as text; their output is unchanged
- Fix: `query_graph` breadth-first traversal and the MCP `query_graph` text no longer depend on set iteration order, so results are identical across runs

## 0.4.28 (2026-05-15)

- Add: deterministic API endpoint extraction for Flask/FastAPI/Django, Express/NestJS/Next.js, Spring, Laravel, Rails, Gin/Echo/Chi, and ASP.NET; endpoint nodes carry `method`, `path`, and `framework`; handler links use `exposes_endpoint`
- Add: `graph.html` highlights endpoint nodes as stars; `GRAPH_REPORT.md` includes an API Endpoints section
- Add: endpoint fixtures, extraction tests, and end-to-end pipeline coverage for extract → build → cluster → analyze → report → export
- Fix: Whisper prompt/model env vars now accept `TRACELY360_WHISPER_*` names while preserving legacy `GRAPHIFY_WHISPER_*` compatibility
- Change: license from MIT to Apache 2.0
- Docs: full doc rewrite — README, ARCHITECTURE, SECURITY recreated from scratch
- Docs: add CONTRIBUTING, CODE_OF_CONDUCT, SUPPORT, and GitHub issue/PR templates for the public repository workflow

## 0.4.24 (2026-04-21)

- Packaging: bump release version to avoid PyPI filename reuse rejection after deleted `0.4.23` artifacts

## 0.4.23 (2026-04-18)

- Fix: stale skill version warning persists after `tracely360 install` when multiple platforms installed — now refreshes `.tracely360_version` in all known skill directories (#178)
- Fix: `.html` files silently skipped during detection — added to `DOC_EXTENSIONS` (#260)
- Fix: `_rebuild_code` fails on graphs > 5000 nodes because `to_html` raises `ValueError` — wrapped in try/except so `graph.json` and `GRAPH_REPORT.md` always land (#432)
- Fix: Go stdlib imports produced `imports_from` edges pointing at local files of the same basename — Go import IDs now prefixed `go_pkg_` (#431)

## 0.4.22 (2026-04-18)

- Fix: AST cache written to `src/tracely360-out/cache/` instead of project root — `extract()` now called with explicit `cache_root` (#429)
- Fix: `.mdx` files silently skipped during detection — added to `DOC_EXTENSIONS` (#428)

## 0.4.21 (2026-04-17)

- Fix: `tracely360 cluster-only` crashed with `KeyError: 'total_files'` — cluster-only skips detection; report now handles missing stats (#422)
- Fix: `/tracely360 --update` dropped existing graph nodes — merged result now serialized before Step 4 (#423)

## 0.4.20 (2026-04-17)

- Fix: JS/MJS `imports_from` edges dropped for `../subdir/file.mjs` style imports — fixed with `os.path.normpath` (#414)
- Fix: `tracely360 update .` and `cluster-only` now generate `graph.html` alongside other outputs (#418)

## 0.4.19 (2026-04-17)

- Fix: AST and semantic extraction no longer produce mismatched node IDs — `build_from_json` normalises IDs before dropping edges (#390)
- Fix: cross-file call resolution extended to Go, Rust, Zig, PowerShell, Elixir (#298)
- Fix: Windows nested output directory bug — `cache_dir` and `_rebuild_code` now call `.resolve()` (#410)
- Fix: `tracely360 hook install` respects `core.hooksPath` git config (#401)
- Fix: Kiro skill YAML frontmatter — `description` value quoted, colons replaced (#385)
- Docs: Windows PATH tip and macOS pipx tip added (#413)
- Docs: team workflow section — committing output, `.tracely360ignore` usage (#369)

## 0.4.16 (2026-04-16)

- Fix: `tracely360 watch` crashed with NameError — missing `import sys` (#386, #394)
- Fix: `.mjs` files detected but produced 0 nodes — added to AST dispatch table (#387)
- Fix: `llm.py` excluded from published wheel (#391)

## 0.4.15 (2026-04-15)

- Feat: VS Code Copilot Chat support — `tracely360 vscode install` (#206)
- Fix: OpenCode plugin path on Windows (#378)
- Fix: Gemini CLI on Windows installs to `~/.agents/skills/` (#368)
- Fix: `.mjs` and `.ejs` recognised as JavaScript (#365, #372)
- Fix: `god_nodes()` field renamed from `edges` to `degree` (#375)
- Fix: macOS `tracely360 watch` uses `PollingObserver` by default (#373)

## 0.4.14 (2026-04-15)

- Fix: cross-file call edges emitted for all languages — previously only Python had cross-file resolution (#348)
- Fix: PHP static method calls and class constant access (#230, #232)
- Fix: `--wiki` flag runs in skill pipeline (#229, #354)
- Fix: `tracely360 install --platform opencode` also installs plugin (#356)
- Fix: `extract()` accepts explicit `cache_root` parameter (#350)
- Fix: `os.replace` falls back to `shutil.copy2` on Windows `PermissionError` (#287)
- Fix: `tracely360 update` exits with code 1 on failure (#287)
- Fix: templates use `tracely360 update .` instead of hardcoded `python3 -c` (#287)
- Fix: `skill-kiro.md` added to package-data (#352)
- Fix: `betweenness_centrality` uses approximate sampling for large graphs (#341)

## 0.4.13 (2026-04-14)

- Add: Verilog/SystemVerilog support (`.v`, `.sv`) via tree-sitter-verilog (#325)
- Fix: hyperedge polygons render correctly on HiDPI/Retina displays (#334)
- Fix: rebuild rule uses `tracely360 update .` instead of hardcoded `python3 -c` (#324)
- Fix: `tracely360 query` handles `label: null` nodes (#323)

## 0.4.12 (2026-04-13)

- Add: Kiro IDE/CLI support — `tracely360 kiro install` (#319, #321)
- Fix: cache `file_hash()` uses relative paths — portable across machines (#311)

## 0.4.11 (2026-04-13)

- Fix: `tracely360 query` on MultiGraph graphs (#305)
- Fix: `tracely360 query` handles null `source_file` (#307)
- Fix: MCP server derives base from absolute graph path (#309)
- Fix: `.tracely360ignore` patterns from parent directories (#303)

## 0.4.10 (2026-04-13)

- Fix: `tracely360 install --platform cursor` crash (#281)
- Fix: `_agents_uninstall` only removes OpenCode plugin for opencode platform (#276)
- Add: `svg = ["matplotlib"]` optional extra (#288)
- Fix: `graspologic` has `python_version < '3.13'` env marker (#290)
- Add: Dart/Flutter support (`.dart`) (#292)
- Add: `norm_label` for diacritic-insensitive search (#293)
- Add: Hermes Agent platform support (#251)
- Add: PHP static property, config, container, event listener extraction (#234, #236, #238, #240)
- Add: `prune_dangling_edges()` utility (#294)
- Fix: Antigravity install improvements (#268)
- Fix: Windows hook tests (#279)
- Add: bare CLI commands `path`, `explain`, `add`, `watch`, `update`, `cluster-only` (#277)

## 0.4.8 (2026-04-12)

- Fix: platform skill files no longer contain Claude-specific language (#272)

## 0.4.7 (2026-04-12)

- Fix: `watch` semantic edge preservation (#269)
- Fix: `tracely360 claw install` writes to `.openclaw/` (#208)
- Add: Blade template support (#242)
- Docs: WSL/Linux MCP setup note (#250)

## 0.4.6 (2026-04-12)

- Add: Google Antigravity support (#203, #199, #53)

## 0.4.5 (2026-04-12)

- Fix: MCP server handles blank lines between JSON messages (#201)

## 0.4.4 (2026-04-12)

- Fix: `watch` preserves INFERRED/AMBIGUOUS edges across rebuilds (#261)
- Fix: Codex hook compatibility with codex-cli 0.120.0 (#249)
- Fix: lockfiles skipped during detection (#266)

## 0.4.3 (2026-04-12)

- Fix: JS/TS relative imports resolve to full-path node IDs (#256)
- Fix: Python relative imports resolve correctly (#256)
- Fix: `watch --rebuild_code` merges with existing semantic nodes (#253)
- Fix: Windows hooks fall back to `python` if `python3` not found (#244)
- Fix: `surprising_connections` / `suggest_questions` handle stale edge hints (#226)
- Add: `.vue` and `.svelte` files recognised (#254)

## 0.4.2 (2026-04-11)

- Fix: same-basename files in different directories — full path IDs (#211)
- Fix: edges using `from`/`to` keys accepted (#216)
- Fix: empty graphs no longer crash `to_html` (#217)
- Fix: post-commit hook extension allowlist updated (#222)
- Fix: NetworkX `links` key accepted alongside `edges` (#212)
- Fix: version warning during install/uninstall (#220)
- Fix: UTF-8 encoding on all file IO; `newline="\n"` for hooks (#204)
- Fix: Obsidian export `.md.md` filenames (#221)

## 0.4.1 (2026-04-10)

- Fix: `collect_files()` respects `.tracely360ignore` (#188)
- Fix: skill subagent type corrected (#195)
- Fix: chunk file warning on missing files

## 0.4.0 (2026-04-10)

- Branch: v4 — video and audio corpus support
- Add: `.mp4`, `.mp3`, `.wav`, `.mov`, `.webm`, `.m4a`, `.ogg`, `.mkv`, `.avi`, `.m4v` transcription via faster-whisper
- Add: YouTube/URL download via yt-dlp
- Add: domain-aware Whisper prompts from corpus god nodes
- Add: `tracely360-out/transcripts/` cache
- Requires: `pip install 'tracely360[video]'`

## 0.3.29 (2026-04-10)

- Add: video/audio corpus support (faster-whisper)
- Add: YouTube/URL download (yt-dlp)
- Add: domain-aware Whisper prompts
- Add: transcript cache

## 0.3.28 (2026-04-10)

- Fix: hook installers always reinstall on re-run (#182)
- Fix: rationale node labels with `\r` on Windows (#176)
- Fix: `skill-windows.md` missing flags (#177)

## 0.3.27 (2026-04-10)

- Fix: `tracely360 install --platform gemini` copies skill to Gemini CLI (#174)

## 0.3.26 (2026-04-10)

- Fix: MCP server path validation for graphs outside cwd

## 0.3.25 (2026-04-09)

- Fix: `gemini` and `cursor` added to `_PLATFORM_CONFIG` (#171)
- Fix: `serve.py` path validation for MCP server (#170)
- Fix: MCP `call_tool()` error handling (#163)
- Fix: `.tracely360ignore` walks parent directories (#168)
- Add: Aider platform support (#74)
- Add: GitHub Copilot CLI platform support (#134)
- Add: `--directed` flag for DiGraph output (#125)
- Add: frontmatter-aware cache for Markdown files (#131)

## 0.3.24 (2026-04-09)

- Fix: `tracely360 codex install` recovery on re-run (#153)

## 0.3.23 (2026-04-09)

- Add: Gemini CLI support (#105)
- Add: sponsor nudge at pipeline completion

## 0.3.22 (2026-04-09)

- Add: Cursor support (#137)
- Fix: `_rebuild_code()` KeyError (#148)
- Fix: `to_json()` crash on NetworkX 3.2.x (#149)

## 0.3.21 (2026-04-09)

- Fix: Codex PreToolUse hook schema (#138)
- Fix: git hooks use `#!/bin/sh` for Windows (#140)

## 0.3.20 (2026-04-09)

- Fix: XSS in interactive HTML graph
- Add: OpenCode plugin (#71)
- Fix: AST call edges carry `confidence=EXTRACTED` (#127)
- Fix: `tree-sitter>=0.23.0` pinned (#89)

## 0.3.19 (2026-04-09)

- Fix: install tries plain `pip install` before `--break-system-packages` (#126)

## 0.3.18 (2026-04-09)

- Fix: `--watch` mode respects `.tracely360ignore` (#120)
- Fix: Codex hook uses `systemMessage` (#121)
- Fix: Trae link corrected (#122)
- Docs: Korean README (#112)
- Refactor: `save_query_result` uses CLI command (#114)

## 0.3.17 (2026-04-08)

- Add: Julia (`.jl`) support (#98)
- Fix: semantic extraction chunks grouped by directory (#65)
- Fix: `tree-sitter>=0.21` pinned (#52)
- Add: progress output every 100 files (#52)

## 0.3.16 (2026-04-08)

- Fix: NetworkX < 3.4 compatibility (#95)
- Fix: `.jsx` files detected and extracted (#94)
- Fix: `.tracely360_python` preserved across runs (#92)

## 0.3.15 (2026-04-08)

- Feat: Trae and Trae CN platform support
- Fix: `skill-droid.md` package data
- Fix: XSS in HTML legend
- Fix: shebang allowlist validation
- Fix: `louvain_communities()` cross-version compatibility
- Fix: pipx detection in git hooks
- Docs: Japanese README

## 0.3.14 (2026-04-08)

- Fix: Codex PreToolUse hook (#86)
- Fix: `--update` prunes ghost nodes (#51)

## 0.3.13 (2026-04-08)

- Fix: PreToolUse hook outputs `additionalContext` (#83)
- Fix: Go AST method receivers use package directory scope (#85)
- Fix: PDFs in Xcode asset catalogs (#52)
- Fix: Python parser crash guarded (#52)
- Fix: skill intermediate files moved to `tracely360-out/` (#81)

## 0.3.12 (2026-04-07)

- Fix: `sanitize_label` double-encoding (#66)
- Fix: `--wiki` flag in usage table (#55)

## 0.3.11 (2026-04-07)

- Fix: Louvain fallback timeout on large sparse graphs (#48)

## 0.3.10 (2026-04-07)

- Fix: Windows UnicodeEncodeError during install (#47)
- Add: skill version staleness check (#46)

## 0.3.9 (2026-04-07)

- Add: `follow_symlinks` parameter (#33)
- Fix: `watch.py` uses `collect_files()` consistently

## 0.3.8 (2026-04-07)

- Add: C# inheritance and interface extraction (#45)
- Add: `tracely360 query` CLI command

## 0.3.7 (2026-04-07)

- Add: Objective-C support (`.m`, `.mm`)
- Add: `--obsidian-dir` flag
- Fix: semantic cache path resolution

## 0.3.0 (2026-04-06)

- Add: multi-platform support — Codex, OpenCode, OpenClaw
- Add: `tracely360 install --platform <codex|opencode|claw>`
- Add: platform install/uninstall commands
- Add: Apache 2.0 license
- Fix: `build()` hyperedge merging
- Refactor: `extract.py` 2527 → 1588 lines — `LanguageConfig` dataclass + `_extract_generic()`

## 0.2.2 (2026-04-06)

- Add: `tracely360 claude install/uninstall`
- Add: `tracely360 hook install/uninstall/status`
- Add: `tracely360 benchmark` CLI command

## 0.1.8 (2026-04-05)

- Fix: follow-up questions check wiki first
- Fix: `--update` auto-regenerates wiki

## 0.1.7 (2026-04-05)

- Add: `--wiki` flag — Wikipedia-style agent-crawlable wiki
- Add: `wiki.py` module with `to_wiki()`

## 0.1.6 (2026-04-05)

- Fix: follow-up questions answered from graph.json instead of re-exploring

## 0.1.5 (2026-04-05)

- Perf: semantic extraction chunks 12-15 → 20-25 files
- Perf: code-only corpora skip semantic dispatch
- Refactor: dead imports removed, helper functions extracted

## 0.1.4 (2026-04-05)

- Replace pyvis with custom vis.js HTML renderer
- HTML graph generated by default
- Token reduction benchmark auto-runs on large corpora
- Fix: stdlib/external edge warnings eliminated
- Fix: `build()` cross-extraction edge merging

## 0.1.3 (2026-04-04)

- Fix: `pyproject.toml` structure
- Add: GitHub repository and issues URLs
- Add: PyPI keywords

## 0.1.1 (2026-04-04)

- Add: CI badge
- Add: ARCHITECTURE.md, SECURITY.md
- Add: `worked/` directory with eval reports

## 0.1.0 (2026-04-03)

Initial release.

- 13-language AST extraction via tree-sitter
- Leiden community detection with oversized community splitting
- SHA256 semantic cache
- MCP stdio server
- Memory feedback loop
- Obsidian vault export
- Security module
- `tracely360 install` CLI
