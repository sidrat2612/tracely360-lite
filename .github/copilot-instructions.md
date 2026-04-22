# Project Guidelines

## Communication
- Bullets over prose. Fewest words that solve the task.
- No restatement, filler, framing, recaps, mid-stream summaries, or progress updates.
- One-line update only if a blocker or user-visible side effect.
- No emojis. No "I will now…", "Here's…", "Let me…".

## Output for tasks
- Report only: (1) blockers/risks, (2) next steps if necessary or high value.
- No file-by-file changelogs unless asked.
- For runs: report only the outcome that matters.
- Do not create docs/markdown to describe changes unless asked.

## Working style
- Default to action when intent is clear.
- Minimal, focused edits. No drive-by refactors, renames, or "improvements".
- Don't add comments, docstrings, or type hints to code you didn't change.
- Don't add error handling for impossible states. Validate at boundaries only.
- Don't create helpers/abstractions for one-time use.

## Code review mode
- Hostile reviewer. Assume code was written by Claude/Codex.
- Lead with concrete defects: bugs, weak assumptions, lazy patterns, overengineering, regressions, hallucinated APIs, perf cliffs, security holes.
- No praise. No softening.

## Coding standards
- **Python**: 3.12+, type hints on public funcs, ruff + mypy clean, pytest, asyncio (no threading unless justified).
- **TS/JS**: strict mode, no `any`, ESLint clean, prefer `unknown` + narrow.
- **Cypher**: parameterized only — never f-string or concat user input. `MERGE` for idempotency, `MATCH` for reads.
- **Imports**: absolute within package, no wildcards, no circular.
- **Naming**: descriptive. No `data`/`info`/`temp`/`tmp` style names.
- **Errors**: specific exceptions, never bare `except`, never silent swallow.
- **Logging**: structured, no secrets/PII, include scan/request IDs.
- **Tests**: every public fn/endpoint covered. Integration tests marked `@pytest.mark.integration`.

## Security (non-negotiable)
- No secrets in code, logs, or commits. Env vars + `pydantic.SecretStr`.
- Cypher/SQL: parameterized queries only. CI lint enforces it.
- API auth required in production; fail-fast on startup if missing.
- Constant-time compare for tokens (`hmac.compare_digest`).
- CORS: explicit allow-list, never `*` in prod.
- Validate all external input (paths, URLs, IDs) at the boundary.
- Reject `file://`, localhost, private IPs in scan targets unless explicit allow-list.
- `pip-audit` / `pnpm audit` clean before release.
- Full OWASP checklist and self-hosting controls: [Traciphy/docs/HOW_IT_WORKS.md](Traciphy/docs/HOW_IT_WORKS.md).

## Operational safety
- Local reversible actions: just do it.
- Destructive/shared actions (rm -rf, force-push, drop table, push, comment on PR, modify infra): confirm first.
- Never bypass checks (`--no-verify`, `--force` without reason).

## Tools
- Prefer workspace tools (file_search, grep_search, read_file) over shell `find`/`grep`/`cat`.
- Read large ranges, not many small ones. Read independent files in parallel.
- Use `search_subagent` for multi-step exploration.
- Never reference tool names in user output.

## Status tracking
- Keep [Traciphy/docs/REMAINING_ROADMAP.md](Traciphy/docs/REMAINING_ROADMAP.md) current when work materially changes delivery status, release readiness, or backlog.
- Implementation phases are complete; use `REMAINING_ROADMAP.md` for both current state and remaining work.
- If a major stream reopens, record it explicitly in `REMAINING_ROADMAP.md` instead of recreating phase-only docs.

## Project context
**Traciphy** = evidence-first code intelligence graph for AI agents.
- Python 3.12 scanner + FastAPI + MCP stdio server
- Neo4j 5.25+ (APOC optional)
- TS/React + Vite frontend
- **No LLM dependency** — agent is the intelligence; Traciphy never calls OpenAI/Anthropic
- Vendored extraction now lives in `traciphy/extraction/`; treat it as first-party vendored code and preserve the upstream provenance notes in `VENDORED.md`.

Canonical edge names: `CALLS_FUNCTION`, `IMPLEMENTS_ENDPOINT`, `DECLARES_{MODULE,CLASS,FUNCTION}`, `IMPORTS_MODULE`, `BELONGS_TO_SERVICE`, `CONTAINS_FILE`, `HAS_ANNOTATION`, `SUGGESTS_LINK`. Do not invent new ones.

Trust levels: `parser_proven` > `agent_accepted` > `agent_suggested`. Never conflate.

15 MCP tools, frozen at Phase 5. Do not add new tool names.

## When lost — read project docs
Source of truth lives in [Traciphy/docs/](Traciphy/docs/). Read the relevant canonical doc before changing code in that area.

| Need | Read |
|---|---|
| Product overview and quick start | [README.md](Traciphy/README.md) |
| Architecture, graph schema, trust model | [ARCHITECTURE.md](Traciphy/docs/ARCHITECTURE.md) |
| Setup, workflows, MCP tools, installers, security, release | [HOW_IT_WORKS.md](Traciphy/docs/HOW_IT_WORKS.md) |
| Current state, release readiness, and backlog | [REMAINING_ROADMAP.md](Traciphy/docs/REMAINING_ROADMAP.md) |

Roadmap + current delivery state: [Traciphy/docs/REMAINING_ROADMAP.md](Traciphy/docs/REMAINING_ROADMAP.md).

If the code and the docs disagree, fix the code or update the canonical doc explicitly in the same PR.