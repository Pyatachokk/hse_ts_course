from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render PDF pages to PNG files.")
    parser.add_argument("pdf", nargs="+", help="PDF files to render.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repository root for resolving relative paths.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output root. Defaults to a temp transcribe-lecture-notes directory.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=3.0,
        help="Render scale. 3.0 is usually enough for handwritten formulas.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise SystemExit(f"Could not find repository root from {start}")


def resolve_repo(path: Path | None) -> Path:
    if path is not None:
        return path.resolve()
    return find_repo_root(Path.cwd())


def resolve_pdf(repo: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    path = path.resolve()
    if not path.exists():
        raise SystemExit(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise SystemExit(f"Not a PDF: {path}")
    return path


def output_root(args: argparse.Namespace) -> Path:
    if args.out_dir is not None:
        return args.out_dir.resolve()
    return Path(tempfile.gettempdir()) / "transcribe-lecture-notes" / "pages"


def render_pdf(pdf: Path, root: Path, scale: float) -> list[Path]:
    try:
        import fitz
    except ImportError:
        raise SystemExit("PyMuPDF is not installed. Run with `uv run --with pymupdf ...`.")

    doc = fitz.open(pdf)
    pdf_dir = root / pdf.stem
    pdf_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    matrix = fitz.Matrix(scale, scale)
    for index, page in enumerate(doc, start=1):
        output = pdf_dir / f"page_{index:02d}.png"
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(output)
        outputs.append(output)
    return outputs


def main() -> int:
    args = parse_args()
    if args.scale <= 0:
        raise SystemExit("--scale must be positive.")
    repo = resolve_repo(args.repo)
    pdfs = [resolve_pdf(repo, value) for value in args.pdf]
    root = output_root(args)

    plan = []
    for pdf in pdfs:
        plan.append({"pdf": str(pdf), "out_dir": str(root / pdf.stem)})
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    for pdf in pdfs:
        outputs = render_pdf(pdf, root, args.scale)
        print(f"{pdf} -> {root / pdf.stem}")
        for output in outputs:
            print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
