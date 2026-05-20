---
name: ts-notes-visualizations
description: Use when creating, adding, drawing, editing, regenerating, or inserting Plotly visualizations for the hse_ts_course time-series lecture notes in lectures/ts_notes.
---

# TS Notes Visualizations

This skill creates and edits figures for `/Users/mzekhov/Projects/hse_ts_course/*/lectures/ts_notes`.

## Workflow

1. Locate the active notes tree:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$SKILL_DIR/scripts/locate_ts_notes.py" --format json
```

2. For a new figure, get naming and chapter context:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$SKILL_DIR/scripts/visualization_context.py" --mode new --chapter 03_ETS --slug english_snake_slug
```

3. Create a self-contained Python script in `chapters/images_code`. Use `plotly.graph_objects` and `plotly.io`; do not use `plotly.express`. The script must compute paths from `Path(__file__)`, save a PNG in `chapters/images`, and be runnable as:

```bash
uv run /absolute/path/to/chapters/images_code/<name>.py
```

4. Run the script, then insert the figure in the target chapter:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$SKILL_DIR/scripts/insert_figure.py" \
  --chapter 03_ETS \
  --image 03_ETS_06_english_snake_slug.png \
  --caption "Russian caption" \
  --label fig:ets_english_snake_slug \
  --after-line 123 \
  --write
```

5. Validate:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$SKILL_DIR/scripts/validate_visualization.py" \
  --chapter 03_ETS \
  --code 03_ETS_06_english_snake_slug.py \
  --image 03_ETS_06_english_snake_slug.png \
  --label fig:ets_english_snake_slug \
  --caption "Russian caption"
```

The validator runs a tiny Plotly PNG export through `uv run --no-sync`; if that fails, fix the project environment manually before regenerating figures.

## Naming

- File base: `{chapter_stem}_{NN}_{english_snake_slug}`.
- Example: `03_ETS_06_new_visualization.py` and `03_ETS_06_new_visualization.png`.
- `chapter_stem` is the chapter file stem, such as `03_ETS`.
- `NN` is one more than the largest existing number for that chapter across `chapters/images` and `chapters/images_code`.
- Default label: `fig:{chapter_key}_{slug}`, where `chapter_key` removes the leading chapter number and lowercases the remaining stem, for example `fig:ets_new_visualization`.

## Figure Format

Insert figures as:

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.9\linewidth]{images/<name>.png}
  \caption{...}
  \label{fig:...}
\end{figure}
```

Inside `enumerate` or `itemize`, preserve the surrounding indentation. Use `\textwidth` only when the nearby chapter already uses it for the same visual context or the user asks.

## Editing Existing Figures

For edits, first run:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ts-notes-visualizations"
uv run python "$SKILL_DIR/scripts/visualization_context.py" --mode edit --image <name>.png
```

Read the existing `.py` and view the existing PNG before changing anything. Make targeted edits to the existing code and regenerate the same PNG unless the user explicitly asks for a new figure. If the PNG exists but the matching code file is missing, ask before recreating or replacing it.

## Defaults

- The active period is the newest `20??-spring` or `20??-fall` directory containing `lectures/ts_notes/ts_notes.tex`.
- Captions and axis labels should be Russian unless the user asks otherwise.
- Legend labels, plot titles, subplot titles, and axis titles must start with a capital letter.
- File slugs are English `snake_case`.
- The skill validates `kaleido`/Plotly export but does not install dependencies.
