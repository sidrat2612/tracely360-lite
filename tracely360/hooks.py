# git hook integration - install/uninstall tracely360 post-commit and post-checkout hooks
from __future__ import annotations
import re
import subprocess
from pathlib import Path

_HOOK_MARKER = "# tracely360-hook-start"
_HOOK_MARKER_END = "# tracely360-hook-end"
_CHECKOUT_MARKER = "# tracely360-checkout-hook-start"
_CHECKOUT_MARKER_END = "# tracely360-checkout-hook-end"

_PYTHON_DETECT = """\
# Detect the correct Python interpreter (handles pipx, venv, system installs)
TRACELY360_BIN=$(command -v tracely360 2>/dev/null)
if [ -n "$TRACELY360_BIN" ]; then
    _SHEBANG=$(head -1 "$TRACELY360_BIN" | sed 's/^#![[:space:]]*//')
    case "$_SHEBANG" in
        */env\\ *) TRACELY360_PYTHON="${_SHEBANG#*/env }" ;;
        *)         TRACELY360_PYTHON="$_SHEBANG" ;;
    esac
    # Allowlist: only keep characters valid in a filesystem path to prevent
    # injection if the shebang contains shell metacharacters
    case "$TRACELY360_PYTHON" in
        *[!a-zA-Z0-9/_.-]*) TRACELY360_PYTHON="" ;;
    esac
    if [ -n "$TRACELY360_PYTHON" ] && ! "$TRACELY360_PYTHON" -c "import tracely360" 2>/dev/null; then
        TRACELY360_PYTHON=""
    fi
fi
# Fall back: try python3, then python (Windows has no python3 shim)
if [ -z "$TRACELY360_PYTHON" ]; then
    if command -v python3 >/dev/null 2>&1 && python3 -c "import tracely360" 2>/dev/null; then
        TRACELY360_PYTHON="python3"
    elif command -v python >/dev/null 2>&1 && python -c "import tracely360" 2>/dev/null; then
        TRACELY360_PYTHON="python"
    else
        exit 0
    fi
fi
"""

_HOOK_SCRIPT = """\
# tracely360-hook-start
# Auto-rebuilds the knowledge graph after each commit (code files only, no LLM needed).
# Installed by: tracely360 hook install

CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD 2>/dev/null)
if [ -z "$CHANGED" ]; then
    exit 0
fi

""" + _PYTHON_DETECT + """
export GRAPHIFY_CHANGED="$CHANGED"
$TRACELY360_PYTHON -c "
import os, sys
from pathlib import Path

changed_raw = os.environ.get('GRAPHIFY_CHANGED', '')
changed = [Path(f.strip()) for f in changed_raw.strip().splitlines() if f.strip()]

if not changed:
    sys.exit(0)

print(f'[tracely360 hook] {len(changed)} file(s) changed - rebuilding graph...')

try:
    from tracely360.watch import _rebuild_code
    _rebuild_code(Path('.'))
except Exception as exc:
    print(f'[tracely360 hook] Rebuild failed: {exc}')
    sys.exit(1)
"
# tracely360-hook-end
"""


_CHECKOUT_SCRIPT = """\
# tracely360-checkout-hook-start
# Auto-rebuilds the knowledge graph (code only) when switching branches.
# Installed by: tracely360 hook install

PREV_HEAD=$1
NEW_HEAD=$2
BRANCH_SWITCH=$3

# Only run on branch switches, not file checkouts
if [ "$BRANCH_SWITCH" != "1" ]; then
    exit 0
fi

# Only run if tracely360-out/ exists (graph has been built before)
if [ ! -d "tracely360-out" ]; then
    exit 0
fi

""" + _PYTHON_DETECT + """
echo "[tracely360] Branch switched - rebuilding knowledge graph (code files)..."
$TRACELY360_PYTHON -c "
from tracely360.watch import _rebuild_code
from pathlib import Path
import sys
try:
    _rebuild_code(Path('.'))
except Exception as exc:
    print(f'[tracely360] Rebuild failed: {exc}')
    sys.exit(1)
"
# tracely360-checkout-hook-end
"""


def _git_root(path: Path) -> Path | None:
    """Walk up to find .git directory."""
    current = path.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _hooks_dir(root: Path) -> Path:
    """Return the git hooks directory, respecting core.hooksPath if set (e.g. Husky)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "core.hooksPath"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            custom = result.stdout.strip()
            if custom:
                p = Path(custom)
                if not p.is_absolute():
                    p = root / p
                p.mkdir(parents=True, exist_ok=True)
                return p
    except (OSError, FileNotFoundError):
        pass
    d = root / ".git" / "hooks"
    d.mkdir(exist_ok=True)
    return d


def _install_hook(hooks_dir: Path, name: str, script: str, marker: str) -> str:
    """Install a single git hook, appending if an existing hook is present."""
    hook_path = hooks_dir / name
    if hook_path.exists():
        content = hook_path.read_text(encoding="utf-8")
        if marker in content:
            return f"already installed at {hook_path}"
        hook_path.write_text(content.rstrip() + "\n\n" + script, encoding="utf-8", newline="\n")
        return f"appended to existing {name} hook at {hook_path}"
    hook_path.write_text("#!/bin/sh\n" + script, encoding="utf-8", newline="\n")
    hook_path.chmod(0o755)
    return f"installed at {hook_path}"


def _uninstall_hook(hooks_dir: Path, name: str, marker: str, marker_end: str) -> str:
    """Remove tracely360 section from a git hook using start/end markers."""
    hook_path = hooks_dir / name
    if not hook_path.exists():
        return f"no {name} hook found - nothing to remove."
    content = hook_path.read_text(encoding="utf-8")
    if marker not in content:
        return f"tracely360 hook not found in {name} - nothing to remove."
    new_content = re.sub(
        rf"{re.escape(marker)}.*?{re.escape(marker_end)}\n?",
        "",
        content,
        flags=re.DOTALL,
    ).strip()
    if not new_content or new_content in ("#!/bin/bash", "#!/bin/sh"):
        hook_path.unlink()
        return f"removed {name} hook at {hook_path}"
    hook_path.write_text(new_content + "\n", encoding="utf-8", newline="\n")
    return f"tracely360 removed from {name} at {hook_path} (other hook content preserved)"


def install(path: Path = Path(".")) -> str:
    """Install tracely360 post-commit and post-checkout hooks in the nearest git repo."""
    root = _git_root(path)
    if root is None:
        raise RuntimeError(f"No git repository found at or above {path.resolve()}")

    hooks_dir = _hooks_dir(root)

    commit_msg = _install_hook(hooks_dir, "post-commit", _HOOK_SCRIPT, _HOOK_MARKER)
    checkout_msg = _install_hook(hooks_dir, "post-checkout", _CHECKOUT_SCRIPT, _CHECKOUT_MARKER)

    return f"post-commit: {commit_msg}\npost-checkout: {checkout_msg}"


def uninstall(path: Path = Path(".")) -> str:
    """Remove tracely360 post-commit and post-checkout hooks."""
    root = _git_root(path)
    if root is None:
        raise RuntimeError(f"No git repository found at or above {path.resolve()}")

    hooks_dir = _hooks_dir(root)
    commit_msg = _uninstall_hook(hooks_dir, "post-commit", _HOOK_MARKER, _HOOK_MARKER_END)
    checkout_msg = _uninstall_hook(hooks_dir, "post-checkout", _CHECKOUT_MARKER, _CHECKOUT_MARKER_END)

    return f"post-commit: {commit_msg}\npost-checkout: {checkout_msg}"


def status(path: Path = Path(".")) -> str:
    """Check if tracely360 hooks are installed."""
    root = _git_root(path)
    if root is None:
        return "Not in a git repository."
    hooks_dir = _hooks_dir(root)

    def _check(name: str, marker: str) -> str:
        p = hooks_dir / name
        if not p.exists():
            return "not installed"
        return "installed" if marker in p.read_text(encoding="utf-8") else "not installed (hook exists but tracely360 not found)"

    commit = _check("post-commit", _HOOK_MARKER)
    checkout = _check("post-checkout", _CHECKOUT_MARKER)
    return f"post-commit: {commit}\npost-checkout: {checkout}"
