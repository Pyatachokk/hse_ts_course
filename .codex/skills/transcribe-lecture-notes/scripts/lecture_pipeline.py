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


@dataclass(frozen=True)
class LectureJob:
    key: str
    video: Path | None
    pdf: Path | None
    audio: Path | None
    expected_audio: Path | None
    transcript: Path | None
    expected_transcript: Path | None
    final_markdown: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare lecture audio, raw transcripts, PDF pages, and markdown validation."
    )
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--year-dir", required=True, help="Year directory such as 2025-spring.")
    parser.add_argument(
        "--lecture",
        action="append",
        default=[],
        help="Lecture filter: number, basename fragment, or title fragment. May be repeated.",
    )
    parser.add_argument("--all", action="store_true", help="Process every lecture in the year.")
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


def normalize(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.lower(), flags=re.UNICODE).split())


def lecture_number(path: Path) -> int | None:
    text = path.stem.lower()
    match = re.search(r"(?:lecture|лекция)[\s_.-]*0*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    digits = re.findall(r"\d+", text)
    if digits:
        return int(digits[0])
    return None


def lecture_key(path: Path) -> str:
    number = lecture_number(path)
    if number is not None:
        return f"lecture-{number:02d}"
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


def expected_audio_path(year_dir: Path, video: Path, audio_format: str) -> Path:
    videos_dir = year_dir / "videos"
    relative = video.relative_to(videos_dir).with_suffix(f".{audio_format}")
    return year_dir / "audio" / "raw" / relative


def expected_transcript_path(year_dir: Path, audio: Path) -> Path:
    audio_root = year_dir / "audio" / "raw"
    try:
        relative = audio.relative_to(audio_root)
    except ValueError:
        relative = Path(audio.name)
    return (year_dir / "transcriptions" / "raw" / relative).with_suffix(".transcript.txt")


def choose_existing_by_key(paths: list[Path], key: str) -> Path | None:
    for path in paths:
        if lecture_key(path) == key:
            return path
    return None


def resolve_jobs(args: argparse.Namespace, repo: Path, year_dir: Path) -> list[LectureJob]:
    videos = iter_files(year_dir / "videos", VIDEO_EXTENSIONS)
    pdfs = iter_files(year_dir / "lectures", {".pdf"})
    new_audio = iter_files(year_dir / "audio" / "raw", AUDIO_EXTENSIONS)
    legacy_audio = iter_files(year_dir / "transcribations", AUDIO_EXTENSIONS)
    new_transcripts = iter_files(year_dir / "transcriptions" / "raw", {".txt", ".json"})
    legacy_transcripts = iter_files(year_dir / "transcribations", {".txt", ".json"})
    new_markdown = iter_files(year_dir / "cleaned_transcriptions", {".md"})
    legacy_markdown = iter_files(year_dir / "cleaned_transcribations", {".md"})

    selected: set[str] = set()
    for path in [*videos, *pdfs, *new_audio, *legacy_audio, *new_transcripts, *legacy_transcripts]:
        if args.all or matches_filter(path, args.lecture):
            selected.add(lecture_key(path))

    if not selected:
        raise SystemExit("No matching lectures found. Pass --lecture or --all.")

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
        expected_audio = expected_audio_path(year_dir, video, args.audio_format) if video else None
        audio = existing_audio or expected_audio
        existing_transcript = (
            choose_existing_by_key(new_transcripts, key)
            or choose_existing_by_key(legacy_transcripts, key)
        )
        expected_transcript = expected_transcript_path(year_dir, audio) if audio else None
        existing_markdown = (
            choose_existing_by_key(new_markdown, key)
            or choose_existing_by_key(legacy_markdown, key)
        )
        final_name = existing_markdown.name if existing_markdown else f"{(pdf or video or audio).stem}.md"
        final_markdown = year_dir / "cleaned_transcriptions" / final_name
        jobs.append(
            LectureJob(
                key=key,
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
    if not args.all and not args.lecture:
        raise SystemExit("Pass --lecture or --all.")

    repo = resolve_repo(args.repo)
    year_dir = resolve_year_dir(repo, args.year_dir)
    jobs = resolve_jobs(args, repo, year_dir)
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
