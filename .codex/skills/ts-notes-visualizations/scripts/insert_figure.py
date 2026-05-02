#!/usr/bin/env -S uv run python
"""Insert a TS notes LaTeX figure block with project-local conventions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from locate_ts_notes import LocateError, locate_ts_notes
from visualization_context import ContextError, resolve_chapter


class InsertError(RuntimeError):
    """User-facing error for figure insertion."""


def resolve_image(images_dir: Path, image: str) -> Path:
    raw = Path(image).expanduser()
    if raw.is_absolute():
        image_path = raw.resolve()
    elif raw.parts and raw.parts[0] == "images":
        image_path = images_dir / raw.name
    else:
        image_path = images_dir / raw.name

    if image_path.suffix.lower() != ".png":
        raise InsertError(f"image must be a .png file: {image}")
    if image_path.parent.resolve() != images_dir.resolve():
        raise InsertError(f"image must live in {images_dir}: {image_path}")
    if not image_path.is_file():
        raise InsertError(f"image file does not exist: {image_path}")
    return image_path


def find_label_usage(ts_notes_dir: Path, label: str) -> list[dict[str, Any]]:
    needle = rf"\label{{{label}}}"
    usages: list[dict[str, Any]] = []
    for path in sorted(ts_notes_dir.rglob("*.tex")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if needle in line:
                usages.append({"path": str(path), "line": number})
    return usages


def find_image_usage(ts_notes_dir: Path, image_name: str) -> list[dict[str, Any]]:
    needle = f"images/{image_name}"
    usages: list[dict[str, Any]] = []
    for path in sorted(ts_notes_dir.rglob("*.tex")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if needle in line:
                usages.append({"path": str(path), "line": number})
    return usages


def infer_figure_indent(lines: list[str], after_line: int) -> str:
    index = after_line - 1
    if index < 0 or index >= len(lines):
        raise InsertError(f"--after-line is outside the chapter: {after_line}")

    previous_item_indent: str | None = None
    environment_depth = 0
    for line in lines[: after_line]:
        stripped = line.strip()
        if stripped.startswith(r"\begin{enumerate}") or stripped.startswith(
            r"\begin{itemize}"
        ):
            environment_depth += 1
            previous_item_indent = None
        elif stripped.startswith(r"\end{enumerate}") or stripped.startswith(
            r"\end{itemize}"
        ):
            environment_depth = max(0, environment_depth - 1)
            previous_item_indent = None
        elif environment_depth and stripped.startswith(r"\item"):
            previous_item_indent = line[: len(line) - len(line.lstrip())]

    if environment_depth and previous_item_indent is not None:
        return previous_item_indent + "  "

    line = lines[index]
    return line[: len(line) - len(line.lstrip())]


def build_block(indent: str, image_name: str, caption: str, label: str, width: str) -> list[str]:
    latex_image = f"images/{image_name}"
    return [
        "",
        rf"{indent}\begin{{figure}}[htbp]",
        rf"{indent}  \centering",
        rf"{indent}  \includegraphics[width={width}]{{{latex_image}}}",
        rf"{indent}  \caption{{{caption}}}",
        rf"{indent}  \label{{{label}}}",
        rf"{indent}\end{{figure}}",
        "",
    ]


def insert_block(chapter_path: Path, after_line: int, block: list[str], write: bool) -> dict[str, Any]:
    lines = chapter_path.read_text(encoding="utf-8").splitlines()
    if after_line < 1 or after_line > len(lines):
        raise InsertError(f"--after-line is outside the chapter: {after_line}")
    updated = lines[:after_line] + block + lines[after_line:]
    if write:
        chapter_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return {
        "chapter_path": str(chapter_path),
        "after_line": after_line,
        "inserted_start_line": after_line + 1,
        "inserted_end_line": after_line + len(block),
        "written": write,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="hse_ts_course repository path")
    parser.add_argument("--chapter", required=True, help="chapter .tex path, stem, or partial name")
    parser.add_argument("--image", required=True, help="PNG name/path under chapters/images")
    parser.add_argument("--caption", required=True, help="LaTeX figure caption")
    parser.add_argument("--label", required=True, help="unique LaTeX label, e.g. fig:ets_slug")
    parser.add_argument("--after-line", type=int, required=True, help="1-based line after which to insert")
    parser.add_argument("--width", default=r"0.9\linewidth", help=r"includegraphics width")
    parser.add_argument("--write", action="store_true", help="write changes; otherwise dry-run")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        loc = locate_ts_notes(args.repo)
        ts_notes_dir = Path(loc["ts_notes_dir"])
        chapters_dir = Path(loc["chapters_dir"])
        images_dir = Path(loc["images_dir"])
        chapter_path = resolve_chapter(chapters_dir, args.chapter)
        image_path = resolve_image(images_dir, args.image)

        label_usages = find_label_usage(ts_notes_dir, args.label)
        if label_usages:
            raise InsertError(
                f"label already exists: {args.label} at "
                + ", ".join(f"{u['path']}:{u['line']}" for u in label_usages)
            )

        image_usages = find_image_usage(ts_notes_dir, image_path.name)
        if image_usages:
            raise InsertError(
                f"image is already included: {image_path.name} at "
                + ", ".join(f"{u['path']}:{u['line']}" for u in image_usages)
            )

        lines = chapter_path.read_text(encoding="utf-8").splitlines()
        indent = infer_figure_indent(lines, args.after_line)
        block = build_block(indent, image_path.name, args.caption, args.label, args.width)
        result = insert_block(chapter_path, args.after_line, block, args.write)
    except (LocateError, ContextError, InsertError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result.update(
        {
            "image": f"images/{image_path.name}",
            "caption": args.caption,
            "label": args.label,
            "width": args.width,
            "block": block,
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
