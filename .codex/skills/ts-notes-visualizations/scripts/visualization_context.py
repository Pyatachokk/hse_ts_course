#!/usr/bin/env -S uv run python
"""Describe naming, paths, and insertion context for TS notes figures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from locate_ts_notes import LocateError, locate_ts_notes


SLUG_RE = re.compile(r"[^a-z0-9]+")


class ContextError(RuntimeError):
    """User-facing error for figure context lookup."""


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("_", value.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        raise ContextError(
            "slug must contain Latin letters or digits; use English snake_case"
        )
    return slug


def resolve_chapter(chapters_dir: Path, chapter: str | None) -> Path:
    if not chapter:
        raise ContextError("chapter is required")

    raw = Path(chapter).expanduser()
    if raw.is_file():
        chapter_path = raw.resolve()
        if chapter_path.suffix != ".tex":
            raise ContextError(f"chapter must be a .tex file: {chapter_path}")
        return chapter_path

    query = raw.stem if raw.suffix == ".tex" else str(raw)
    candidates = sorted(chapters_dir.glob("*.tex"))
    exact = [path for path in candidates if path.stem == query or path.name == query]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ContextError(
            "ambiguous chapter: " + ", ".join(path.name for path in exact)
        )

    partial = [
        path
        for path in candidates
        if query.lower() in path.stem.lower() or query.lower() in path.name.lower()
    ]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ContextError(
            "ambiguous chapter: " + ", ".join(path.name for path in partial)
        )
    raise ContextError(f"chapter not found in {chapters_dir}: {chapter}")


def infer_chapter_from_stem(chapters_dir: Path, stem: str) -> Path:
    matches = sorted(
        path for path in chapters_dir.glob("*.tex") if stem.startswith(path.stem + "_")
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        matches.sort(key=lambda path: len(path.stem), reverse=True)
        if len(matches) == 1 or len(matches[0].stem) > len(matches[1].stem):
            return matches[0]
        raise ContextError(
            "ambiguous chapter for figure stem: "
            + ", ".join(path.name for path in matches)
        )
    raise ContextError(f"cannot infer chapter from figure stem: {stem}")


def scan_existing(chapter_stem: str, images_dir: Path, code_dir: Path) -> list[dict[str, Any]]:
    pattern = re.compile(rf"^{re.escape(chapter_stem)}_(\d{{2,}})_(.+)$")
    entries: list[dict[str, Any]] = []
    for kind, directory, suffix in (
        ("image", images_dir, ".png"),
        ("code", code_dir, ".py"),
    ):
        if not directory.exists():
            continue
        for path in sorted(directory.glob(f"{chapter_stem}_*{suffix}")):
            match = pattern.match(path.stem)
            if not match:
                continue
            number, slug = match.groups()
            entries.append(
                {
                    "kind": kind,
                    "number": int(number),
                    "number_text": number,
                    "slug": slug,
                    "name": path.name,
                    "path": str(path),
                }
            )
    return sorted(entries, key=lambda item: (item["number"], item["kind"], item["name"]))


def next_number(entries: list[dict[str, Any]]) -> int:
    if not entries:
        return 1
    return max(entry["number"] for entry in entries) + 1


def chapter_key(chapter_stem: str) -> str:
    key = re.sub(r"^\d+_?", "", chapter_stem)
    return slugify(key)


def insertion_points(chapter_path: Path) -> list[dict[str, Any]]:
    lines = chapter_path.read_text(encoding="utf-8").splitlines()
    points: list[dict[str, Any]] = []
    markers = (
        r"\section",
        r"\subsection",
        r"\subsubsection",
        r"\paragraph",
        r"\item",
    )
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if stripped.startswith(markers):
            if stripped.startswith(r"\item"):
                kind = r"\item"
            else:
                kind = stripped.split("{", 1)[0].strip()
            points.append(
                {
                    "line": number,
                    "kind": kind,
                    "text": stripped[:160],
                }
            )
    return points


def resolve_edit_target(
    images_dir: Path,
    code_dir: Path,
    chapter_path: Path | None,
    image: str | None,
    slug: str | None,
) -> tuple[str, Path, Path]:
    stems: set[str] = set()
    for directory, suffix in ((images_dir, ".png"), (code_dir, ".py")):
        if directory.exists():
            stems.update(path.stem for path in directory.glob(f"*{suffix}"))

    if image:
        raw = Path(image).expanduser()
        stem = raw.stem
    elif slug:
        wanted = slugify(slug)
        matches = [
            stem for stem in stems if stem.endswith("_" + wanted) or wanted in stem
        ]
        if chapter_path:
            matches = [
                stem for stem in matches if stem.startswith(chapter_path.stem + "_")
            ]
        matches = sorted(matches)
        if len(matches) != 1:
            if not matches:
                raise ContextError(f"no existing figure matches slug: {wanted}")
            raise ContextError("ambiguous figure slug: " + ", ".join(matches))
        stem = matches[0]
    else:
        raise ContextError("edit mode requires --image or --slug")

    if chapter_path and not stem.startswith(chapter_path.stem + "_"):
        raise ContextError(
            f"figure {stem} does not match chapter stem {chapter_path.stem}"
        )

    return stem, images_dir / f"{stem}.png", code_dir / f"{stem}.py"


def build_new_context(args: argparse.Namespace, loc: dict[str, str]) -> dict[str, Any]:
    chapters_dir = Path(loc["chapters_dir"])
    images_dir = Path(loc["images_dir"])
    code_dir = Path(loc["images_code_dir"])
    chapter_path = resolve_chapter(chapters_dir, args.chapter)
    slug = slugify(args.slug or "")
    entries = scan_existing(chapter_path.stem, images_dir, code_dir)
    number = next_number(entries)
    number_text = f"{number:02d}"
    base = f"{chapter_path.stem}_{number_text}_{slug}"

    return {
        "mode": "new",
        "ts_notes": loc,
        "chapter": {"stem": chapter_path.stem, "path": str(chapter_path)},
        "existing": entries,
        "naming": {
            "slug": slug,
            "number": number,
            "number_text": number_text,
            "base": base,
            "code_name": f"{base}.py",
            "image_name": f"{base}.png",
            "label": f"fig:{chapter_key(chapter_path.stem)}_{slug}",
        },
        "paths": {
            "code_path": str(code_dir / f"{base}.py"),
            "image_path": str(images_dir / f"{base}.png"),
            "latex_image_path": f"images/{base}.png",
        },
        "latex": {
            "default_width": r"0.9\linewidth",
            "insertion_points": insertion_points(chapter_path),
        },
    }


def build_edit_context(args: argparse.Namespace, loc: dict[str, str]) -> dict[str, Any]:
    chapters_dir = Path(loc["chapters_dir"])
    images_dir = Path(loc["images_dir"])
    code_dir = Path(loc["images_code_dir"])
    chapter_path = resolve_chapter(chapters_dir, args.chapter) if args.chapter else None
    if not chapter_path and args.image:
        chapter_path = infer_chapter_from_stem(chapters_dir, Path(args.image).stem)

    stem, image_path, code_path = resolve_edit_target(
        images_dir, code_dir, chapter_path, args.image, args.slug
    )
    if not chapter_path:
        chapter_path = infer_chapter_from_stem(chapters_dir, stem)

    image_exists = image_path.is_file()
    code_exists = code_path.is_file()
    if image_exists and code_exists:
        state = "ready"
        requires_permission = False
    elif image_exists and not code_exists:
        state = "image_without_code"
        requires_permission = True
    elif code_exists and not image_exists:
        state = "code_without_image"
        requires_permission = False
    else:
        raise ContextError(f"neither image nor code exists for {stem}")

    return {
        "mode": "edit",
        "ts_notes": loc,
        "chapter": {"stem": chapter_path.stem, "path": str(chapter_path)},
        "target": {
            "base": stem,
            "image_name": image_path.name,
            "code_name": code_path.name,
            "image_path": str(image_path),
            "code_path": str(code_path),
            "latex_image_path": f"images/{image_path.name}",
            "image_exists": image_exists,
            "code_exists": code_exists,
            "state": state,
            "requires_permission": requires_permission,
        },
        "latex": {"insertion_points": insertion_points(chapter_path)},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="hse_ts_course repository path")
    parser.add_argument("--mode", choices=("new", "edit"), required=True)
    parser.add_argument("--chapter", help="chapter .tex path, stem, or partial name")
    parser.add_argument("--slug", help="English snake_case slug")
    parser.add_argument("--image", help="existing image name/path for edit mode")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        loc = locate_ts_notes(args.repo)
        if args.mode == "new":
            data = build_new_context(args, loc)
        else:
            data = build_edit_context(args, loc)
    except (LocateError, ContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
