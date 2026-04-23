# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.4.x | Yes |
| < 0.4 | No |

## Reporting a vulnerability

Do not open a public GitHub issue for security vulnerabilities.

Email siddharth.rathore2612@gmail.com with:

- a description of the issue
- reproduction steps
- expected impact
- a suggested fix, if you have one

Reports are acknowledged within 72 hours when possible.

## Security model

tracely360 is a local development tool. It runs as a CLI, assistant skill, and optional MCP stdio server. It does not execute source code during analysis, and it does not make network calls during graph analysis except for explicit user-requested ingestion flows such as `ingest` and `add`.

## Threat model

| Vector | Mitigation |
|--------|-----------|
| SSRF via URL fetch | `security.validate_url()` allows only `http` and `https`, blocks private/loopback/link-local/cloud-metadata IPs, and re-validates redirects |
| Oversized downloads | `safe_fetch()` aborts at 50 MB; `safe_fetch_text()` aborts at 10 MB |
| Non-2xx HTTP responses | `safe_fetch()` raises `HTTPError`; error pages are not silently treated as content |
| Path traversal in MCP server | `validate_graph_path()` resolves paths and requires them to stay inside `tracely360-out/` |
| XSS in HTML export | `sanitize_label()` strips control characters, truncates, and HTML-escapes labels and titles |
| Prompt injection via labels | `sanitize_label()` is applied to MCP text output |
| YAML injection | `_yaml_str()` escapes backslashes, quotes, and newlines before YAML frontmatter output |
| Encoding crashes | Tree-sitter bytes are decoded with `errors="replace"` |
| Route discovery side effects | Endpoint extraction is AST-only: no code execution, port probing, or HTTP calls to discovered endpoints |
| Symlink traversal | `os.walk(..., followlinks=False)` is used throughout `detect.py` |
| Corrupted graph data | `json.JSONDecodeError` is caught with a clear recovery message |
| Open redirects in fetch | Each redirect hop is validated against the same URL blocklist |

## What tracely360 does not do

- Run a network listener during normal analysis work
- Execute code from source files
- Probe running services or open ports to discover routes
- Use `shell=True` in subprocess calls
- Store credentials or API keys
- Call external LLM APIs as part of core analysis

## Sensitive file exclusion

`detect.py` excludes common secret and generated-file patterns by default, including:

- `*.pem`, `*.key`, `*.p12`, `*.pfx`
- `.env`, `.env.*`
- common credential-like filenames
- `node_modules/`, `venv/`, `.venv/`, `dist/`, `build/`, `__pycache__/`

Custom exclusions can be added with `.tracely360ignore` using gitignore syntax.
