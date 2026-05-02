# Agent Instructions

## Repository Codex Skill

This repository ships the `ts-notes-visualizations` Codex skill at:

```text
.codex/skills/ts-notes-visualizations
```

When setting up this repository on another machine, install or refresh the skill with:

```bash
REPO_DIR="$(git rev-parse --show-toplevel)"
CODEX_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$CODEX_SKILLS_DIR"
rm -rf "$CODEX_SKILLS_DIR/ts-notes-visualizations"
cp -R "$REPO_DIR/.codex/skills/ts-notes-visualizations" "$CODEX_SKILLS_DIR/"
```

Verify the install from the repository root:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$SKILL_DIR/scripts/locate_ts_notes.py" --repo "$PWD" --format json
```

When invoking skill helper scripts, always use `uv run python ...`; do not run them with bare `python`, `python3`, or direct script execution.
