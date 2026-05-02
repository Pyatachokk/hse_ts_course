#!/usr/bin/env -S uv run python
"""Validate a TS notes Plotly visualization, PNG, and LaTeX insertion."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from locate_ts_notes import LocateError, locate_ts_notes
from visualization_context import ContextError, resolve_chapter


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class ValidationError(RuntimeError):
    """User-facing validation failure."""


def resolve_code(code_dir: Path, code: str) -> Path:
    raw = Path(code).expanduser()
    if raw.is_absolute():
        code_path = raw.resolve()
    else:
        name = raw.name if raw.suffix else raw.name + ".py"
        code_path = code_dir / name
    if code_path.suffix != ".py":
        raise ValidationError(f"code must be a .py file: {code}")
    if code_path.parent.resolve() != code_dir.resolve():
        raise ValidationError(f"code must live in {code_dir}: {code_path}")
    if not code_path.is_file():
        raise ValidationError(f"code file does not exist: {code_path}")
    return code_path


def resolve_image(images_dir: Path, image: str) -> Path:
    raw = Path(image).expanduser()
    if raw.is_absolute():
        image_path = raw.resolve()
    elif raw.parts and raw.parts[0] == "images":
        image_path = images_dir / raw.name
    else:
        name = raw.name if raw.suffix else raw.name + ".png"
        image_path = images_dir / name
    if image_path.suffix.lower() != ".png":
        raise ValidationError(f"image must be a .png file: {image}")
    if image_path.parent.resolve() != images_dir.resolve():
        raise ValidationError(f"image must live in {images_dir}: {image_path}")
    if not image_path.is_file():
        raise ValidationError(f"image file does not exist: {image_path}")
    return image_path


def validate_no_plotly_express(code_path: Path) -> dict[str, Any]:
    source = code_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(code_path))
    except SyntaxError as exc:
        raise ValidationError(f"code has a syntax error: {exc}") from exc

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "plotly.express":
                    violations.append(f"import plotly.express at line {node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "plotly.express":
                violations.append(f"from plotly.express import ... at line {node.lineno}")
            if module == "plotly" and any(alias.name == "express" for alias in node.names):
                violations.append(f"from plotly import express at line {node.lineno}")

    if violations:
        raise ValidationError("plotly.express is not allowed: " + "; ".join(violations))
    return {"code_no_plotly_express": True}


def validate_png(image_path: Path) -> dict[str, Any]:
    header = image_path.read_bytes()[: len(PNG_HEADER)]
    if header != PNG_HEADER:
        raise ValidationError(f"file is not a valid PNG: {image_path}")
    return {"png_header": True, "image_size_bytes": image_path.stat().st_size}


def validate_tex(chapter_path: Path, image_name: str, label: str, caption: str | None) -> dict[str, Any]:
    text = chapter_path.read_text(encoding="utf-8")
    include_re = re.compile(
        r"\\includegraphics(?:\[[^\]]*\])?\{images/" + re.escape(image_name) + r"\}"
    )
    if not include_re.search(text):
        raise ValidationError(f"chapter does not include images/{image_name}")
    if rf"\label{{{label}}}" not in text:
        raise ValidationError(f"chapter does not contain label {label}")
    caption_ok = None
    if caption is not None:
        caption_ok = rf"\caption{{{caption}}}" in text
        if not caption_ok:
            raise ValidationError("chapter does not contain the expected caption")
    return {"tex_include": True, "tex_label": True, "tex_caption": caption_ok}


def validate_export_dependencies(repo_dir: Path, timeout: int) -> dict[str, Any]:
    uv = shutil.which("uv")
    if not uv:
        raise ValidationError("uv is not available on PATH")

    script = r"""
from pathlib import Path
import tempfile

import plotly.graph_objects as go
import plotly.io as pio

fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1], mode="lines")])
with tempfile.TemporaryDirectory() as tmpdir:
    output = Path(tmpdir) / "plotly_export_check.png"
    pio.write_image(fig, output, width=200, height=120, scale=1)
    if output.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("plotly export did not create a valid PNG")
"""
    try:
        result = subprocess.run(
            [uv, "run", "--no-sync", "python", "-c", script],
            cwd=repo_dir,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(f"Plotly export dependency check timed out after {timeout}s") from exc

    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        tail = "\n".join(output.splitlines()[-40:])
        raise ValidationError(
            "Plotly PNG export is not available through `uv run --no-sync`:\n" + tail
        )
    return {"plotly_png_export": True}


def run_latex(ts_notes_dir: Path, timeout: int) -> dict[str, Any]:
    latexmk = shutil.which("latexmk")
    if not latexmk:
        raise ValidationError("latexmk is not available on PATH")
    command = [
        latexmk,
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "ts_notes.tex",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ts_notes_dir,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(f"latexmk timed out after {timeout}s") from exc

    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        tail = "\n".join(output.splitlines()[-40:])
        raise ValidationError(f"latexmk failed with exit code {result.returncode}:\n{tail}")
    return {"latexmk": True}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="hse_ts_course repository path")
    parser.add_argument("--chapter", required=True, help="chapter .tex path, stem, or partial name")
    parser.add_argument("--code", required=True, help="Python script name/path under chapters/images_code")
    parser.add_argument("--image", required=True, help="PNG name/path under chapters/images")
    parser.add_argument("--label", required=True, help="expected LaTeX label")
    parser.add_argument("--caption", help="expected LaTeX caption")
    parser.add_argument(
        "--skip-export-deps",
        action="store_true",
        help="skip the Plotly/Kaleido PNG export dependency check",
    )
    parser.add_argument(
        "--export-deps-timeout",
        type=int,
        default=60,
        help="Plotly export dependency check timeout in seconds",
    )
    parser.add_argument("--skip-latex", action="store_true", help="skip latexmk smoke test")
    parser.add_argument("--latex-timeout", type=int, default=120, help="latexmk timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    checks: dict[str, Any] = {}
    try:
        loc = locate_ts_notes(args.repo)
        chapter_path = resolve_chapter(Path(loc["chapters_dir"]), args.chapter)
        code_path = resolve_code(Path(loc["images_code_dir"]), args.code)
        image_path = resolve_image(Path(loc["images_dir"]), args.image)
        if code_path.stem != image_path.stem:
            raise ValidationError(
                f"code and image names must share one base: {code_path.name} vs {image_path.name}"
            )

        if args.skip_export_deps:
            checks["plotly_png_export"] = "skipped"
        else:
            checks.update(validate_export_dependencies(Path(loc["repo_dir"]), args.export_deps_timeout))
        checks.update(validate_no_plotly_express(code_path))
        checks.update(validate_png(image_path))
        checks.update(validate_tex(chapter_path, image_path.name, args.label, args.caption))
        if args.skip_latex:
            checks["latexmk"] = "skipped"
        else:
            checks.update(run_latex(Path(loc["ts_notes_dir"]), args.latex_timeout))
    except (LocateError, ContextError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "chapter": str(chapter_path),
                "code": str(code_path),
                "image": str(image_path),
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
