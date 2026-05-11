---
name: transcribe-lecture-notes
description: Use when turning hse_ts_course lecture or seminar videos/audio and PDF materials into raw transcriptions and cleaned markdown notes by extracting audio, transcribing sequentially through OpenAI or an OpenAI-compatible API, visually checking PDF pages, and validating LaTeX.
---

# Transcribe Lecture Notes

This skill builds committed transcription artifacts from course videos and PDF materials.

## Directory Contract

Before running the pipeline, decide which semantic content folder the user requested:

```text
lectures -> --kind lectures
seminars -> --kind seminars
```

All new videos, audio, raw transcripts, and cleaned transcripts must stay inside that folder:

```text
<year>/
  lectures/
    videos/
    audio/raw/
    transcriptions/
      raw/
      cleaned/
  seminars/
    videos/
    audio/raw/
    transcriptions/
      raw/
      cleaned/
```

Legacy year-level lecture folders such as `<year>/audio/raw`, `<year>/transcriptions/raw`, `<year>/cleaned_transcriptions`, `transcribations/`, and `cleaned_transcribations/` may be read as inputs, but new lecture outputs must go to `<year>/lectures/...`. Seminar outputs must go to `<year>/seminars/...`.

Name raw and cleaned transcript files from the English note/PDF stem when one exists:

```text
<year>/<kind>/lecture_01_intro.pdf
<year>/<kind>/transcriptions/raw/lecture_01_intro.transcript.txt
<year>/<kind>/transcriptions/cleaned/lecture_01_intro.md
```

Do not name new raw transcripts from Russian audio/video titles when an English PDF or cleaned markdown name is available.

## Environment

Load `.env` from the repository root before running `uv` commands. Helper scripts read transcription client and request configuration from the environment only; they do not read `.env` directly.

```bash
set -a && source "$REPO_DIR/.env" && set +a
```

Provider selection is deterministic:

1. If `OPENAI_API_KEY` is set, use OpenAI Audio Transcriptions with `OPENAI_TRANSCRIBE_MODEL`.
2. Otherwise, if `CIB_LLM_API_KEY` or `LLM_API_KEY` is set, use the CIB LLM API fallback with:
   - `CIB_LLM_BASE_URL` or `LLM_API_BASE_URL`
   - `CIB_LLM_TRANSCRIBE_MODEL` or `LLM_TRANSCRIBE_MODEL`
   - `CIB_LLM_TRANSCRIBE_MAX_REQUEST_SECONDS` or `LLM_TRANSCRIBE_MAX_REQUEST_SECONDS` for the per-request audio duration limit; default is `3600`
   - `CIB_LLM_TRANSCRIBE_CHUNK_SECONDS` or `LLM_TRANSCRIBE_CHUNK_SECONDS` to override local chunk length; defaults to the same value as the CIB duration limit
3. Otherwise use a custom OpenAI-compatible Audio API from `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, and `OPENAI_COMPATIBLE_TRANSCRIBE_MODEL`.
4. If no provider is configured, stop with a clear error. Do not ask the user to paste keys in chat.

Set request defaults in `.env`, especially `LECTURE_TRANSCRIBE_LANGUAGE` and `LECTURE_TRANSCRIBE_RESPONSE_FORMAT`.
For CIB LLM API, batch transcription automatically uses one-hour chunks. Override with `--cib-max-request-seconds` or `--cib-chunk-seconds` only when that deployment's limit differs.

## Workflow

1. Locate repo and skill directories:

```bash
REPO_DIR="$(git rev-parse --show-toplevel)"
TRANSCRIBE_NOTES_DIR="$REPO_DIR/.codex/skills/transcribe-lecture-notes"
AUDIO_SKILL_DIR="$REPO_DIR/.codex/skills/extract-video-audio"
```

2. Preview the deterministic pipeline:

```bash
set -a && source "$REPO_DIR/.env" && set +a
uv run python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$REPO_DIR" \
  --year-dir 2025-spring \
  --kind lectures \
  --lecture 12 \
  --dry-run
```

3. Extract missing audio and transcribe sequentially:

```bash
set -a && source "$REPO_DIR/.env" && set +a
uv run --with openai python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$REPO_DIR" \
  --year-dir 2025-spring \
  --kind lectures \
  --lecture 12 \
  --extract-audio \
  --transcribe
```

4. Render PDF pages to a temporary directory for visual inspection:

```bash
set -a && source "$REPO_DIR/.env" && set +a
uv run --with pymupdf python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$REPO_DIR" \
  --year-dir 2025-spring \
  --kind lectures \
  --lecture 12 \
  --render-pdf
```

5. Read the rendered PDF pages visually, compare them with the raw transcript, restore a coherent lecture or seminar note, and save it as:

```text
<year>/<kind>/transcriptions/cleaned/<lecture-or-seminar title>.md
```

Use subagents for page-by-page PDF extraction when helpful. The main agent must validate and reconcile the final markdown.

6. Validate the final markdown:

```bash
set -a && source "$REPO_DIR/.env" && set +a
uv run --with markdown-it-py --with pylatexenc python "$TRANSCRIBE_NOTES_DIR/scripts/validate_markdown.py" \
  2025-spring/lectures/transcriptions/cleaned/Lecture_12_garch.md \
  --check-contains "20.9"
```

For seminars, use `--kind seminars` and either `--seminar`, `--item`, or `--all`:

```bash
set -a && source "$REPO_DIR/.env" && set +a
uv run --with openai python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$REPO_DIR" \
  --year-dir 2025-spring \
  --kind seminars \
  --seminar 08 \
  --extract-audio \
  --transcribe
```

## Helper Scripts

- `lecture_pipeline.py`: resolves lecture or seminar assets and optionally extracts audio, transcribes, renders PDFs, and validates a final markdown file.
- `transcribe_audio.py`: provider-aware sequential transcription with local ffmpeg chunking for large files.
- `render_pdf_pages.py`: renders PDFs to temporary PNG page images.
- `validate_markdown.py`: checks Markdown parsing and LaTeX delimiter/braces sanity.

Always invoke helper scripts with `uv run python ...`; add `--with openai`, `--with pymupdf`, `--with markdown-it-py`, or `--with pylatexenc` when those packages are needed.
