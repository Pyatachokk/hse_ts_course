#!/usr/bin/env -S uv run python
"""Locate the newest hse_ts_course lectures/ts_notes tree."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_REPO = Path("/Users/mzekhov/Projects/hse_ts_course")
PERIOD_RE = re.compile(r"^(20\d{2})-(spring|fall)$")
TERM_RANK = {"spring": 1, "fall": 2}


class LocateError(RuntimeError):
    """User-facing error for invalid notes discovery state."""


def _period_sort_key(path: Path) -> tuple[int, int, str]:
    match = PERIOD_RE.match(path.name)
    if not match:
        raise LocateError(f"not a period directory: {path}")
    year, term = match.groups()
    return int(year), TERM_RANK[term], path.name


def find_repo(repo: str | Path | None = None) -> Path:
    repo_path = Path(repo).expanduser() if repo else DEFAULT_REPO
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise LocateError(f"repository does not exist: {repo_path}")
    if not repo_path.is_dir():
        raise LocateError(f"repository path is not a directory: {repo_path}")
    return repo_path


def find_periods(repo: Path) -> list[Path]:
    periods: list[Path] = []
    for child in repo.iterdir():
        if not child.is_dir() or not PERIOD_RE.match(child.name):
            continue
        if (child / "lectures" / "ts_notes" / "ts_notes.tex").is_file():
            periods.append(child)
    return sorted(periods, key=_period_sort_key)


def locate_ts_notes(repo: str | Path | None = None) -> dict[str, str]:
    repo_path = find_repo(repo)
    periods = find_periods(repo_path)
    if not periods:
        raise LocateError(
            "no 20??-spring/fall directory with lectures/ts_notes/ts_notes.tex "
            f"found under {repo_path}"
        )

    period_dir = periods[-1]
    ts_notes_dir = period_dir / "lectures" / "ts_notes"
    chapters_dir = ts_notes_dir / "chapters"
    images_dir = chapters_dir / "images"
    images_code_dir = chapters_dir / "images_code"

    return {
        "repo_dir": str(repo_path),
        "period_name": period_dir.name,
        "period_dir": str(period_dir),
        "ts_notes_dir": str(ts_notes_dir),
        "main_tex": str(ts_notes_dir / "ts_notes.tex"),
        "chapters_dir": str(chapters_dir),
        "images_dir": str(images_dir),
        "images_code_dir": str(images_code_dir),
    }


def _print_text(data: dict[str, str]) -> None:
    for key in (
        "repo_dir",
        "period_name",
        "period_dir",
        "ts_notes_dir",
        "chapters_dir",
        "images_dir",
        "images_code_dir",
    ):
        print(f"{key}={data[key]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(DEFAULT_REPO),
        help=f"hse_ts_course repository path (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="output format (default: json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = locate_ts_notes(args.repo)
    except LocateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        _print_text(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
