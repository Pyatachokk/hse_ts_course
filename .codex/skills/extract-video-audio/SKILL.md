---
name: extract-video-audio
description: Use when extracting audio tracks from hse_ts_course lecture or seminar video files into committed content-level audio/raw folders for transcription pipelines.
---

# Extract Video Audio

This skill extracts audio from course videos into `audio/raw` directories inside the content folder being transcribed.

## Directory Contract

Choose the semantic content folder first:

```text
<year>/lectures/videos/  ->  <year>/lectures/audio/raw/
<year>/seminars/videos/  ->  <year>/seminars/audio/raw/
```

Legacy `<year>/videos/` inputs are still accepted for lectures, but new outputs should be written under `<year>/lectures/audio/raw/`.

## Workflow

1. Locate the repository root and the skill directory:

```bash
REPO_DIR="$(git rev-parse --show-toplevel)"
SKILL_DIR="$REPO_DIR/.codex/skills/extract-video-audio"
```

2. Preview what will be extracted before writing files:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$REPO_DIR" \
  --year-dir 2026-spring \
  --kind lectures \
  --dry-run
```

3. Extract audio. The script creates `audio/raw` automatically and writes one audio file per input video:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$REPO_DIR" \
  --year-dir 2026-spring \
  --kind lectures
```

For seminars, use `--kind seminars`.

4. Check the generated files and git status. `videos` directories are ignored, but `audio/raw` directories are intended to be committed.

## Script Behavior

- The default kind for `--year-dir 2026-spring` is lectures.
- The default input for `--year-dir 2026-spring --kind lectures` is `2026-spring/lectures/videos`.
- The default output is `2026-spring/lectures/audio/raw`.
- For nested videos, preserve the relative path under the selected content folder's `audio/raw`.
- Default output format is `.m4a` with AAC audio suitable for transcription workflows.
- Existing outputs are skipped unless `--overwrite` is passed.
- `ffmpeg` must be installed and available on `PATH`; the script reports a clear error if it is missing.
- Use `--legacy-transcribations` only when intentionally writing to the old `transcribations` layout inside the selected content folder.

## Examples

Extract one file:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$REPO_DIR" \
  --kind lectures \
  2026-spring/lectures/videos/lecture_01.mp4
```

Extract seminar videos:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$REPO_DIR" \
  --year-dir 2026-spring \
  --kind seminars
```

Extract every lecture video in every year directory that has a lecture `videos` folder:

```bash
uv run python "$SKILL_DIR/scripts/extract_audio.py" \
  --repo "$REPO_DIR" \
  --kind lectures \
  --all-years
```
