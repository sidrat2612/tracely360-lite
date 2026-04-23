# Contributing to tracely360

Thank you for helping improve tracely360. This project follows the public-maintainer guidance in https://opensource.guide/: keep the process documented, keep discussion public, and make changes easy to review.

## Project scope

- tracely360 is a local, deterministic code-intelligence tool.
- AST extraction, graph building, and endpoint discovery should stay reproducible and explainable.
- The project does not add hosted LLM dependencies for core analysis.
- Large feature ideas should start as an issue before a pull request.

## Good contributions

- Reproducible bug reports with sample files or fixtures
- Targeted bug fixes with tests
- New language or framework extraction coverage
- Performance improvements with benchmarks or before/after evidence
- Docs, examples, and onboarding improvements

## Before you open an issue or PR

- Search existing issues and pull requests first.
- For support or usage questions, follow [SUPPORT.md](SUPPORT.md).
- For security issues, follow [SECURITY.md](SECURITY.md).
- For community behavior problems, follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]" pytest build twine
```

## Run checks

For most changes, run the narrowest relevant tests first and then the full suite if your change has broad impact.

```bash
pytest
python -m build
python -m twine check dist/*
```

If you add or change extraction behavior, include or update fixtures in `tests/fixtures/`.

## Pull request rules

- Keep changes focused. Avoid drive-by refactors.
- Explain the user-visible problem and why this fix is the right scope.
- Add or update tests for behavior changes.
- Update docs when commands, flags, outputs, or supported frameworks change.
- Add a short note to `CHANGELOG.md` for user-visible changes.
- Open an issue before starting large features or behavior changes.

## Review expectations

- Maintainer time is limited and review is best effort.
- A maintainer will try to acknowledge new issues and PRs within 7 days.
- If a thread is blocked and there has been no response after 7 days, post a short follow-up in the same thread instead of opening a duplicate.

## Communication

- Use public GitHub issues and pull requests for bugs, proposals, and design discussion.
- Keep private contact for security reports or sensitive code of conduct matters only.
- Look for `good first issue` and `help wanted` labels when they are available.