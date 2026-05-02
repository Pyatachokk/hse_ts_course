---
name: extract-video-audio
description: Use when extracting audio tracks from hse_ts_course lecture video files into committed year-level audio/raw folders for transcription pipelines.
---

# Extract Video Audio

This skill extracts audio from course videos into `audio/raw` directories next to year-level `videos` directories.

## Workflow

1. Locate the repository root and the skill directory:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/extract-video-audio"
```

2. Preview what will be extracted before writing files:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$PWD" \
  --year-dir 2026-spring \
  --dry-run
```

3. Extract audio. The script creates `audio/raw` automatically and writes one audio file per input video:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$PWD" \
  --year-dir 2026-spring
```

4. Check the generated files and git status. `videos` directories are ignored, but `audio/raw` directories are intended to be committed.

## Script Behavior

- The default input for `--year-dir 2026-spring` is `2026-spring/videos`.
- The default output is `2026-spring/audio/raw`.
- For nested videos, preserve the relative path under `audio/raw`.
- Default output format is `.m4a` with AAC audio suitable for transcription workflows.
- Existing outputs are skipped unless `--overwrite` is passed.
- `ffmpeg` must be installed and available on `PATH`; the script reports a clear error if it is missing.
- Use `--legacy-transcribations` only when intentionally writing to the old `transcribations` layout.

## Examples

Extract one file:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$PWD" \
  2026-spring/videos/lecture_01.mp4
```

Extract every video in every year directory that has a `videos` folder:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$PWD" \
  --all-years
```
