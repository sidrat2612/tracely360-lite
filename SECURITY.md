# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.4.x | Yes |
| < 0.4 | No |

## Reporting a vulnerability

Email siddharth.rathore2612@gmail.com with a description and reproduction steps. You will receive a response within 72 hours. Please do not open public issues for security vulnerabilities.

## What tracely360-lite does NOT do

- Run a network listener (MCP uses stdio only)
- Execute code from source files
- Probe running services or open ports
- Use `shell=True` in subprocess calls
- Store credentials or API keys
- Call external LLM APIs (no OpenAI, Anthropic, etc.)

## Threat model

| Vector | Mitigation |
|--------|-----------|
| SSRF via URL fetch | `security.validate_url()` blocks `file://`, `ftp://`, private/loopback/link-local/cloud-metadata IPs |
| Oversized downloads | `safe_fetch()` streams and aborts at 50 MB; `safe_fetch_text()` at 10 MB |
| Non-2xx HTTP responses | Error pages are not silently treated as content |
| Path traversal (MCP) | `validate_graph_path()` requires resolved path inside `tracely360-lite-out/` |
| XSS in HTML export | `sanitize_label()` strips control characters, caps at 256 chars, HTML-escapes |
| Prompt injection via labels | `sanitize_label()` applied to all MCP text output |
| YAML injection | `_yaml_str()` escapes backslashes, quotes, newlines |
| Encoding crashes | Tree-sitter bytes decoded with `errors="replace"` |
| Route discovery side effects | Static AST only — no code execution, no port probing, no HTTP requests to discovered endpoints |
| Symlink traversal | `os.walk(..., followlinks=False)` throughout `detect.py` |
| Corrupted graph.json | `json.JSONDecodeError` caught with clear recovery message |
| Open redirects in fetch | Redirect chain validated — each hop checked against the same URL blocklist |

## Security boundaries

### URL validation (`security.validate_url`)

Blocks:
- `file://`, `ftp://`, non-HTTP schemes
- Private IPs (10.x, 172.16-31.x, 192.168.x)
- Loopback (127.x, ::1)
- Link-local (169.254.x, fe80::)
- Cloud metadata (169.254.169.254)

### Fetch wrappers (`security.safe_fetch`, `security.safe_fetch_text`)

- Streaming download with size enforcement
- Redirect chain validation
- Binary cap: 50 MB, text cap: 10 MB
- Configurable timeout (default 30s binary, 15s text)

### Path validation (`security.validate_graph_path`)

- Resolves symlinks and `..` sequences
- Rejects paths that escape `tracely360-lite-out/`
- Used by MCP server before serving any file

### Label sanitization (`security.sanitize_label`)

- Strips control characters (U+0000–U+001F, U+007F–U+009F)
- Truncates to 256 characters
- Applied before HTML rendering and MCP text output

## Sensitive file exclusion

`detect.py` excludes by default:
- `*.pem`, `*.key`, `*.p12`, `*.pfx`
- `.env`, `.env.*`
- Files matching common credential patterns
- `node_modules/`, `venv/`, `.venv/`, `dist/`, `build/`, `__pycache__/`

Custom exclusions via `.tracely360liteignore` (gitignore syntax).
# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.4.x   | Yes       |
| < 0.4   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues via GitHub's private vulnerability reporting, or email the maintainer directly. Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Security Model

tracely360-lite is a **local development tool**. It runs as a CLI, assistant skill, and optionally as a local MCP stdio server. It makes no network calls during graph analysis - only during explicit ingestion flows such as `ingest` / `add` against user-provided URLs.

### Threat Surface

| Vector | Mitigation |
|--------|-----------|
| SSRF via URL fetch | `security.validate_url()` allows only `http` and `https` schemes, blocks private/loopback/link-local IPs, and blocks cloud metadata endpoints. Redirect targets are re-validated. All fetch paths including tweet oEmbed go through `safe_fetch()`. |
| Oversized downloads | `safe_fetch()` streams responses and aborts at 50 MB. `safe_fetch_text()` aborts at 10 MB. |
| Non-2xx HTTP responses | `safe_fetch()` raises `HTTPError` on non-2xx status codes - error pages are not silently treated as content. |
| Path traversal in MCP server | `security.validate_graph_path()` resolves paths and requires them to be inside `tracely360-lite-out/`. Also requires the `tracely360-lite-out/` directory to exist. |
| XSS in graph HTML output | `security.sanitize_label()` strips control characters, caps at 256 chars, and HTML-escapes node labels and edge titles before they are handed to the vis.js renderer. |
| Prompt injection via node labels | `sanitize_label()` also applied to MCP text output - node labels from user-controlled source files cannot break the text format returned to agents. |
| YAML frontmatter injection | `_yaml_str()` escapes backslashes, double quotes, and newlines before embedding user-controlled strings (webpage titles, query questions) in YAML frontmatter. |
| Encoding crashes on source files | All tree-sitter byte slices decoded with `errors="replace"` - non-UTF-8 source files degrade gracefully instead of crashing extraction. |
| Route discovery side effects | API endpoint extraction is static only - tracely360-lite parses framework ASTs and file paths; it does not boot apps, probe ports, or make HTTP requests to discover routes. |
| Symlink traversal | `os.walk(..., followlinks=False)` is explicit throughout `detect.py`. |
| Corrupted graph.json | `_load_graph()` in `serve.py` wraps `json.JSONDecodeError` and prints a clear recovery message instead of crashing. |

### What tracely360-lite does NOT do

- Does not run a network listener (MCP server communicates over stdio only)
- Does not execute code from source files (tree-sitter parses ASTs - no eval/exec)
- Does not probe running services to discover API endpoints
- Does not use `shell=True` in any subprocess call
- Does not store credentials or API keys

### Optional network calls

- `ingest` subcommand: fetches URLs explicitly provided by the user
- PDF extraction: reads local files only (pypdf does not make network calls)
- watch mode: local filesystem events only (watchdog does not make network calls)
