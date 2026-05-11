from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".3gp", ".avi", ".flv", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm", ".wmv"}
AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".mpga", ".oga", ".ogg", ".wav", ".webm"}
CONTENT_KINDS = ("lectures", "seminars")


@dataclass(frozen=True)
class LectureJob:
    key: str
    kind: str
    content_root: Path
    video: Path | None
    pdf: Path | None
    audio: Path | None
    expected_audio: Path | None
    transcript: Path | None
    expected_transcript: Path | None
    final_markdown: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare lecture or seminar audio, raw transcripts, PDF pages, "
            "and markdown validation."
        )
    )
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--year-dir", required=True, help="Year directory such as 2025-spring.")
    parser.add_argument(
        "--kind",
        choices=CONTENT_KINDS,
        default="lectures",
        help=(
            "Content folder inside the year directory. Use lectures for lecture "
            "materials and seminars for seminar materials."
        ),
    )
    parser.add_argument(
        "--lecture",
        action="append",
        default=[],
        help=(
            "Lecture filter: number, basename fragment, or title fragment. "
            "May be repeated."
        ),
    )
    parser.add_argument(
        "--seminar",
        action="append",
        default=[],
        help=(
            "Seminar filter alias: number, basename fragment, or title fragment. "
            "May be repeated."
        ),
    )
    parser.add_argument(
        "--item",
        action="append",
        default=[],
        help=(
            "Generic content filter for either lectures or seminars. May be repeated."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every item in the selected content folder.",
    )
    parser.add_argument("--extract-audio", action="store_true")
    parser.add_argument("--transcribe", action="store_true")
    parser.add_argument("--render-pdf", action="store_true")
    parser.add_argument(
        "--validate-md",
        action="append",
        default=[],
        help="Final markdown file to validate. May be repeated.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audio-format", choices=["m4a", "mp3", "wav"], default="m4a")
    parser.add_argument("--language", default=None)
    parser.add_argument(
        "--cib-max-request-seconds",
        type=int,
        default=None,
        help=(
            "CIB LLM API maximum audio duration per transcription request. "
            "Forwarded only to the transcription step."
        ),
    )
    parser.add_argument(
        "--cib-chunk-seconds",
        type=int,
        default=None,
        help="Seconds per local ffmpeg chunk for CIB LLM API transcription.",
    )
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


def resolve_year_dir(repo: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    path = path.resolve()
    if not path.exists() or not path.is_dir():
        raise SystemExit(f"Year directory not found: {path}")
    return path


def resolve_content_root(year_dir: Path, kind: str) -> Path:
    content_root = year_dir / kind
    if not content_root.exists() or not content_root.is_dir():
        raise SystemExit(f"Content directory not found: {content_root}")
    return content_root


def normalize(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.lower(), flags=re.UNICODE).split())


def lecture_number(path: Path) -> int | None:
    text = path.stem.lower()
    match = re.search(
        r"(?:lecture|лекция|seminar|семинар|sem)[\s_.-]*0*(\d+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1))
    digits = re.findall(r"\d+", text)
    if digits:
        return int(digits[0])
    return None


def item_prefix(path: Path) -> str:
    text = path.stem.lower()
    if re.search(r"(?:seminar|семинар|sem)[\s_.-]*\d*", text, re.IGNORECASE):
        return "seminar"
    if re.search(r"(?:lecture|лекция)[\s_.-]*\d*", text, re.IGNORECASE):
        return "lecture"
    return "item"


def lecture_key(path: Path) -> str:
    number = lecture_number(path)
    if number is not None:
        return f"{item_prefix(path)}-{number:02d}"
    return normalize(path.stem)


def matches_filter(path: Path, filters: list[str]) -> bool:
    if not filters:
        return False
    path_norm = normalize(path.stem)
    number = lecture_number(path)
    for raw_filter in filters:
        item = raw_filter.strip()
        if not item:
            continue
        if item.isdigit() and number == int(item):
            return True
        item_path = Path(item)
        item_number = lecture_number(item_path)
        if item_number is not None and number == item_number:
            return True
        if normalize(item) in path_norm:
            return True
    return False


def iter_files(root: Path, extensions: set[str]) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions
    )


def first_by_key(paths: list[Path]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in paths:
        result.setdefault(lecture_key(path), path)
    return result


def relative_to_named_parent(path: Path, parent_name: str) -> Path:
    for parent in path.parents:
        if parent.name == parent_name:
            return path.relative_to(parent)
    return Path(path.name)


def expected_audio_path(content_root: Path, video: Path, audio_format: str) -> Path:
    relative = relative_to_named_parent(video, "videos").with_suffix(f".{audio_format}")
    return content_root / "audio" / "raw" / relative


def expected_transcript_path(content_root: Path, name_source: Path) -> Path:
    return (
        content_root / "transcriptions" / "raw" / f"{name_source.stem}.transcript.txt"
    )


def choose_existing_by_key(paths: list[Path], key: str) -> Path | None:
    for path in paths:
        if lecture_key(path) == key:
            return path
    return None


def requested_filters(args: argparse.Namespace) -> list[str]:
    return [*args.lecture, *args.seminar, *args.item]


def legacy_roots(year_dir: Path, content_root: Path, kind: str) -> dict[str, list[Path]]:
    roots = {
        "audio": [content_root / "transcribations"],
        "transcripts": [content_root / "transcribations"],
        "markdown": [
            content_root / "cleaned_transcriptions",
            content_root / "cleaned_transcribations",
        ],
    }
    if kind == "lectures":
        roots["audio"].extend([year_dir / "audio" / "raw", year_dir / "transcribations"])
        roots["transcripts"].extend(
            [year_dir / "transcriptions" / "raw", year_dir / "transcribations"]
        )
        roots["markdown"].extend(
            [
                year_dir / "transcriptions" / "cleaned",
                year_dir / "cleaned_transcriptions",
                year_dir / "cleaned_transcribations",
            ]
        )
    return roots


def resolve_jobs(
    args: argparse.Namespace,
    year_dir: Path,
    content_root: Path,
) -> list[LectureJob]:
    filters = requested_filters(args)
    videos = [
        *iter_files(content_root / "videos", VIDEO_EXTENSIONS),
        *(
            iter_files(year_dir / "videos", VIDEO_EXTENSIONS)
            if args.kind == "lectures"
            else []
        ),
    ]
    pdfs = iter_files(content_root, {".pdf"})
    new_audio = iter_files(content_root / "audio" / "raw", AUDIO_EXTENSIONS)
    roots = legacy_roots(year_dir, content_root, args.kind)
    legacy_audio = [
        path for root in roots["audio"] for path in iter_files(root, AUDIO_EXTENSIONS)
    ]
    new_transcripts = iter_files(content_root / "transcriptions" / "raw", {".txt", ".json"})
    legacy_transcripts = [
        path for root in roots["transcripts"] for path in iter_files(root, {".txt", ".json"})
    ]
    new_markdown = iter_files(content_root / "transcriptions" / "cleaned", {".md"})
    legacy_markdown = [
        path for root in roots["markdown"] for path in iter_files(root, {".md"})
    ]

    selected: set[str] = set()
    for path in [
        *videos,
        *pdfs,
        *new_audio,
        *legacy_audio,
        *new_transcripts,
        *legacy_transcripts,
        *new_markdown,
        *legacy_markdown,
    ]:
        if args.all or matches_filter(path, filters):
            selected.add(lecture_key(path))

    if not selected:
        raise SystemExit(
            "No matching items found. Pass --lecture, --seminar, --item, or --all."
        )

    videos_by_key = first_by_key(videos)
    pdfs_by_key = first_by_key(pdfs)
    jobs: list[LectureJob] = []
    for key in sorted(selected):
        video = videos_by_key.get(key)
        pdf = pdfs_by_key.get(key)
        existing_audio = (
            choose_existing_by_key(new_audio, key)
            or choose_existing_by_key(legacy_audio, key)
        )
        expected_audio = expected_audio_path(content_root, video, args.audio_format) if video else None
        audio = existing_audio or expected_audio
        existing_markdown = (
            choose_existing_by_key(new_markdown, key)
            or choose_existing_by_key(legacy_markdown, key)
        )
        existing_transcript = (
            choose_existing_by_key(new_transcripts, key)
            or choose_existing_by_key(legacy_transcripts, key)
        )
        name_source = pdf or existing_markdown or video or audio or existing_transcript
        if name_source is None:
            raise SystemExit(f"{key}: could not resolve a source name for markdown.")
        expected_transcript = (
            expected_transcript_path(content_root, name_source) if audio else None
        )
        final_markdown = content_root / "transcriptions" / "cleaned" / f"{name_source.stem}.md"
        jobs.append(
            LectureJob(
                key=key,
                kind=args.kind,
                content_root=content_root,
                video=video,
                pdf=pdf,
                audio=audio,
                expected_audio=expected_audio,
                transcript=existing_transcript,
                expected_transcript=expected_transcript,
                final_markdown=final_markdown,
            )
        )
    return jobs


def path_or_none(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def print_plan(jobs: list[LectureJob]) -> None:
    print(
        json.dumps(
            [
                {
                    "key": job.key,
                    "kind": job.kind,
                    "content_root": str(job.content_root),
                    "video": path_or_none(job.video),
                    "pdf": path_or_none(job.pdf),
                    "audio": path_or_none(job.audio),
                    "expected_audio": path_or_none(job.expected_audio),
                    "transcript": path_or_none(job.transcript),
                    "expected_transcript": path_or_none(job.expected_transcript),
                    "final_markdown": str(job.final_markdown),
                }
                for job in jobs
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


def run_command(command: list[str], dry_run: bool) -> None:
    if dry_run:
        print("DRY RUN:", " ".join(command))
        return
    subprocess.run(command, check=True)


def run_extract(repo: Path, jobs: list[LectureJob], args: argparse.Namespace) -> None:
    videos = [job.video for job in jobs if job.video is not None]
    if not videos:
        print("No videos to extract.")
        return
    script = repo / ".codex" / "skills" / "extract-video-audio" / "scripts" / "extract_audio.py"
    command = [
        sys.executable,
        str(script),
        "--repo",
        str(repo),
        "--kind",
        args.kind,
        "--format",
        args.audio_format,
    ]
    if args.overwrite:
        command.append("--overwrite")
    if args.dry_run:
        command.append("--dry-run")
    command.extend(str(video) for video in videos)
    run_command(command, False)


def run_transcribe(repo: Path, jobs: list[LectureJob], args: argparse.Namespace) -> None:
    script = Path(__file__).with_name("transcribe_audio.py")
    for job in jobs:
        audio = job.expected_audio if job.expected_audio and job.expected_audio.exists() else job.audio
        if audio is None:
            raise SystemExit(f"{job.key}: no audio available for transcription.")
        if args.dry_run and not audio.exists():
            print(f"DRY RUN: {job.key}: transcript would wait for audio: {audio}")
            continue
        if not args.dry_run and not audio.exists():
            raise SystemExit(f"{job.key}: audio file not found: {audio}")
        output = job.expected_transcript or audio.with_suffix(".transcript.txt")
        command = [
            sys.executable,
            str(script),
            str(audio),
            "--repo",
            str(repo),
            "--out",
            str(output),
        ]
        if args.language:
            command.extend(["--language", args.language])
        if args.cib_max_request_seconds is not None:
            command.extend(
                ["--cib-max-request-seconds", str(args.cib_max_request_seconds)]
            )
        if args.cib_chunk_seconds is not None:
            command.extend(["--cib-chunk-seconds", str(args.cib_chunk_seconds)])
        if args.overwrite:
            command.append("--overwrite")
        if args.dry_run:
            command.append("--dry-run")
        run_command(command, False)


def run_render(repo: Path, jobs: list[LectureJob], args: argparse.Namespace) -> None:
    pdfs = [job.pdf for job in jobs if job.pdf is not None]
    if not pdfs:
        print("No PDFs to render.")
        return
    script = Path(__file__).with_name("render_pdf_pages.py")
    command = [sys.executable, str(script), "--repo", str(repo)]
    if args.dry_run:
        command.append("--dry-run")
    command.extend(str(pdf) for pdf in pdfs)
    run_command(command, False)


def run_validate(markdown_paths: list[str]) -> None:
    script = Path(__file__).with_name("validate_markdown.py")
    command = [sys.executable, str(script), *markdown_paths]
    subprocess.run(command, check=True)


def main() -> int:
    args = parse_args()
    if not args.all and not requested_filters(args):
        raise SystemExit("Pass --lecture, --seminar, --item, or --all.")

    repo = resolve_repo(args.repo)
    year_dir = resolve_year_dir(repo, args.year_dir)
    content_root = resolve_content_root(year_dir, args.kind)
    jobs = resolve_jobs(args, year_dir, content_root)
    print_plan(jobs)

    if args.extract_audio:
        run_extract(repo, jobs, args)
    if args.transcribe:
        run_transcribe(repo, jobs, args)
    if args.render_pdf:
        run_render(repo, jobs, args)
    if args.validate_md:
        run_validate(args.validate_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
