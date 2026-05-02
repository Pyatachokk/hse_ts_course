---
name: transcribe-lecture-notes
description: Use when turning hse_ts_course lecture videos/audio and PDF lecture notes into raw transcriptions and cleaned markdown notes by extracting audio, transcribing sequentially through OpenAI or an OpenAI-compatible API, visually checking PDF pages, and validating LaTeX.
---

# Transcribe Lecture Notes

This skill builds committed lecture artifacts from course videos and PDF notes.

## Directory Contract

Use the corrected year-level layout for new outputs:

```text
<year>/
  videos/
  lectures/
  audio/raw/
  transcriptions/raw/
  cleaned_transcriptions/
```

Legacy `transcribations/` and `cleaned_transcribations/` may be read as inputs, but new outputs must go to `transcriptions/raw` and `cleaned_transcriptions`.

## Environment

Load `.env` from the repository root when present. Provider selection is deterministic:

1. If `OPENAI_API_KEY` is set, use OpenAI Audio Transcriptions with `OPENAI_TRANSCRIBE_MODEL` or `gpt-4o-mini-transcribe`.
2. Otherwise use the OpenAI-compatible Audio API from `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, and `OPENAI_COMPATIBLE_TRANSCRIBE_MODEL`.
3. If neither provider is configured, stop with a clear error. Do not ask the user to paste keys in chat.

Default language is `LECTURE_TRANSCRIBE_LANGUAGE` or `ru`.

## Workflow

1. Locate repo and skill directories:

```bash
TRANSCRIBE_NOTES_DIR="${CODEX_HOME:-$HOME/.codex}/skills/transcribe-lecture-notes"
AUDIO_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/extract-video-audio"
```

2. Preview the deterministic pipeline:

```bash
uv run python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$PWD" \
  --year-dir 2025-spring \
  --lecture 12 \
  --dry-run
```

3. Extract missing audio and transcribe sequentially:

```bash
uv run --with openai python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$PWD" \
  --year-dir 2025-spring \
  --lecture 12 \
  --extract-audio \
  --transcribe
```

4. Render PDF pages to a temporary directory for visual inspection:

```bash
uv run --with pymupdf python "$TRANSCRIBE_NOTES_DIR/scripts/lecture_pipeline.py" \
  --repo "$PWD" \
  --year-dir 2025-spring \
  --lecture 12 \
  --render-pdf
```

5. Read the rendered PDF pages visually, compare them with the raw transcript, restore a coherent lecture note, and save it as:

```text
<year>/cleaned_transcriptions/<lecture title>.md
```

Use subagents for page-by-page PDF extraction when helpful. The main agent must validate and reconcile the final markdown.

6. Validate the final markdown:

```bash
uv run --with markdown-it-py --with pylatexenc python "$TRANSCRIBE_NOTES_DIR/scripts/validate_markdown.py" \
  2025-spring/cleaned_transcriptions/"Лекция 12. GARCH.md" \
  --check-contains "20.9"
```

## Helper Scripts

- `lecture_pipeline.py`: resolves lecture assets and optionally extracts audio, transcribes, renders PDFs, and validates a final markdown file.
- `transcribe_audio.py`: provider-aware sequential transcription with local ffmpeg chunking for large files.
- `render_pdf_pages.py`: renders PDFs to temporary PNG page images.
- `validate_markdown.py`: checks Markdown parsing and LaTeX delimiter/braces sanity.

Always invoke helper scripts with `uv run python ...`; add `--with openai`, `--with pymupdf`, `--with markdown-it-py`, or `--with pylatexenc` when those packages are needed.
