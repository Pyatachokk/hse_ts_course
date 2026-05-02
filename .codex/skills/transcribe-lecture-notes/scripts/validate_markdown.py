from __future__ import annotations

import argparse
import re
from pathlib import Path


DISPLAY_MATH_RE = re.compile(r"\$\$(.*?)\$\$", re.S)
INLINE_MATH_RE = re.compile(r"\\\((.*?)\\\)", re.S)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate cleaned lecture markdown and LaTeX snippets."
    )
    parser.add_argument("markdown", nargs="+", help="Markdown files to validate.")
    parser.add_argument(
        "--check-contains",
        action="append",
        default=[],
        help="Literal text that must be present. May be repeated.",
    )
    return parser.parse_args()


def check_balanced_braces(expr: str) -> str | None:
    depth = 0
    escaped = False
    for char in expr:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        if depth < 0:
            return "unmatched closing brace"
    if depth != 0:
        return "unbalanced braces"
    return None


def parse_markdown(text: str, path: Path) -> None:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        return
    MarkdownIt().parse(text)


def parse_latex(expr: str) -> None:
    try:
        from pylatexenc.latexwalker import LatexWalker
    except ImportError:
        return
    LatexWalker(expr).get_latex_nodes(pos=0)


def validate_file(path: Path, required_literals: list[str]) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    parse_markdown(text, path)

    if text.count("$$") % 2:
        raise SystemExit(f"{path}: odd number of $$ math delimiters")

    for literal in required_literals:
        if literal not in text:
            raise SystemExit(f"{path}: required literal not found: {literal}")

    display = [match.group(1).strip() for match in DISPLAY_MATH_RE.finditer(text)]
    inline = [match.group(1).strip() for match in INLINE_MATH_RE.finditer(text)]
    for kind, expressions in (("display", display), ("inline", inline)):
        for index, expr in enumerate(expressions, start=1):
            brace_error = check_balanced_braces(expr)
            if brace_error:
                raise SystemExit(f"{path}: {kind} math #{index}: {brace_error}")
            try:
                parse_latex(expr)
            except Exception as exc:
                raise SystemExit(f"{path}: {kind} math #{index}: {exc}") from exc
    return len(display), len(inline)


def main() -> int:
    args = parse_args()
    for value in args.markdown:
        path = Path(value)
        if not path.exists():
            raise SystemExit(f"Markdown file not found: {path}")
        display_count, inline_count = validate_file(path, args.check_contains)
        print(
            f"OK {path}: {display_count} display formula(s), "
            f"{inline_count} inline formula(s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
