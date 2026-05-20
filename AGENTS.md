# Agent Instructions

## Editing `ts_notes`

In `*/lectures/ts_notes/chapters/*.tex`, keep prose easy to edit in diffs:
put each new sentence on a new physical line in the `.tex` file.
Do not reflow whole paragraphs into single long lines.
For Russian-language prose, use Russian guillemets (`«ёлочки»`) for quotation marks.
Do not use straight double quotes (`"пример"`) or English curly quotes in visible Russian text.

## Repository Codex Skills

This repository ships Codex skills at:

```text
.codex/skills/extract-video-audio
.codex/skills/transcribe-lecture-notes
.codex/skills/ts-notes-visualizations
```

When setting up this repository on another machine, install or refresh the skills with:

```bash
REPO_DIR="$(git rev-parse --show-toplevel)"
CODEX_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$CODEX_SKILLS_DIR"
for SKILL_NAME in extract-video-audio transcribe-lecture-notes ts-notes-visualizations; do
  rm -rf "$CODEX_SKILLS_DIR/$SKILL_NAME"
  cp -R "$REPO_DIR/.codex/skills/$SKILL_NAME" "$CODEX_SKILLS_DIR/"
done
```

Verify the install from the repository root:

```bash
TS_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$TS_SKILL_DIR/scripts/locate_ts_notes.py" --repo "$PWD" --format json

AUDIO_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/extract-video-audio"
uv run python "$AUDIO_SKILL_DIR/scripts/extract_audio.py" --repo "$PWD" --help

LECTURE_TRANSCRIBE_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/transcribe-lecture-notes"
uv run python "$LECTURE_TRANSCRIBE_SKILL_DIR/scripts/lecture_pipeline.py" --repo "$PWD" --year-dir 2025-spring --lecture 12 --dry-run
```

When invoking skill helper scripts, always use `uv run python ...`; do not run them with bare `python`, `python3`, or direct script execution.
