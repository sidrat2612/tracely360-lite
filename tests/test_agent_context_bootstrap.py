"""Tests for first-run project context bootstrapping from slash skills."""
from pathlib import Path
import json

import pytest

from tracely360.__main__ import (
    _AGENTS_MD_MARKER,
    _CLAUDE_MD_MARKER,
    _KIRO_STEERING_MARKER,
    _VSCODE_INSTRUCTIONS_MARKER,
    ensure_platform_context,
)


def test_ensure_vscode_context_writes_copilot_instructions(tmp_path):
    ensure_platform_context("vscode", tmp_path)
    instructions = tmp_path / ".github" / "copilot-instructions.md"
    assert instructions.exists()
    assert _VSCODE_INSTRUCTIONS_MARKER in instructions.read_text(encoding="utf-8")


def test_ensure_vscode_context_replaces_existing_section(tmp_path):
    instructions = tmp_path / ".github" / "copilot-instructions.md"
    instructions.parent.mkdir(parents=True, exist_ok=True)
    instructions.write_text("## tracely360\nOld text\n", encoding="utf-8")

    ensure_platform_context("vscode", tmp_path)

    content = instructions.read_text(encoding="utf-8")
    assert "Old text" not in content
    assert "GRAPH_REPORT.md" in content


def test_ensure_copilot_context_aliases_vscode_instructions(tmp_path):
    ensure_platform_context("copilot", tmp_path)
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()


def test_ensure_codex_context_writes_agents_and_hook(tmp_path):
    ensure_platform_context("codex", tmp_path)

    agents_md = tmp_path / "AGENTS.md"
    hooks_path = tmp_path / ".codex" / "hooks.json"

    assert agents_md.exists()
    assert _AGENTS_MD_MARKER in agents_md.read_text(encoding="utf-8")

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert hooks["hooks"]["PreToolUse"]


def test_ensure_opencode_context_writes_agents_and_plugin(tmp_path):
    ensure_platform_context("opencode", tmp_path)

    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".opencode" / "plugins" / "tracely360.js").exists()

    config = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert ".opencode/plugins/tracely360.js" in config["plugin"]


def test_ensure_windows_context_writes_claude_md_and_hook(tmp_path):
    ensure_platform_context("windows", tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    settings_path = tmp_path / ".claude" / "settings.json"

    assert claude_md.exists()
    assert _CLAUDE_MD_MARKER in claude_md.read_text(encoding="utf-8")

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["hooks"]["PreToolUse"]


def test_ensure_kiro_context_writes_steering(tmp_path):
    ensure_platform_context("kiro", tmp_path)
    steering = tmp_path / ".kiro" / "steering" / "tracely360.md"
    assert steering.exists()
    assert _KIRO_STEERING_MARKER in steering.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("skill_name", "bootstrap_snippet"),
    [
        ("skill-vscode.md", "ensure_platform_context('vscode'"),
        ("skill-copilot.md", "ensure_platform_context('copilot'"),
        ("skill-codex.md", "ensure_platform_context('codex'"),
        ("skill-opencode.md", "ensure_platform_context('opencode'"),
        ("skill-claw.md", "ensure_platform_context('claw'"),
        ("skill-droid.md", "ensure_platform_context('droid'"),
        ("skill-trae.md", "ensure_platform_context('trae'"),
        ("skill-aider.md", "ensure_platform_context('aider'"),
        ("skill-kiro.md", "ensure_platform_context('kiro'"),
        ("skill-windows.md", "ensure_platform_context('windows'"),
    ],
)
def test_skill_files_bootstrap_project_context(skill_name, bootstrap_snippet):
    import tracely360

    skill = (Path(tracely360.__file__).parent / skill_name).read_text(encoding="utf-8")
    assert bootstrap_snippet in skill