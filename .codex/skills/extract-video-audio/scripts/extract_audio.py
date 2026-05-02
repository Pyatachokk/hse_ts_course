from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".flv",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}

YEAR_DIR_PATTERN = re.compile(r"^20\d{2}-(spring|fall)$")


@dataclass(frozen=True)
class ExtractionPlan:
    source: Path
    output: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract audio from hse_ts_course videos into sibling "
            "audio/raw directories."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Video files, videos directories, or year directories to process.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repository root. Defaults to the nearest parent containing .git.",
    )
    parser.add_argument(
        "--year-dir",
        action="append",
        default=[],
        help="Year directory to process, such as 2026-spring. May be repeated.",
    )
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="Process every 20??-spring/fall directory that has a videos folder.",
    )
    parser.add_argument(
        "--format",
        choices=["m4a", "mp3", "wav"],
        default="m4a",
        help="Output audio format. Defaults to m4a.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing extracted audio files.",
    )
    parser.add_argument(
        "--legacy-transcribations",
        action="store_true",
        help=(
            "Write outputs to the old sibling transcribations directory instead "
            "of the default audio/raw directory."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned extraction paths without running ffmpeg.",
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


def resolve_input(repo: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def is_year_dir(path: Path) -> bool:
    return path.is_dir() and YEAR_DIR_PATTERN.match(path.name) is not None


def iter_video_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def output_for_video(source: Path, audio_format: str, legacy_transcribations: bool) -> Path:
    videos_dir = nearest_videos_dir(source)
    output_parts = ("transcribations",) if legacy_transcribations else ("audio", "raw")
    if videos_dir is None:
        output_root = source.parent.joinpath(*output_parts)
        relative = source.name
    else:
        output_root = videos_dir.parent.joinpath(*output_parts)
        relative = source.relative_to(videos_dir)
    return (output_root / relative).with_suffix(f".{audio_format}")


def nearest_videos_dir(source: Path) -> Path | None:
    for parent in source.parents:
        if parent.name == "videos" and is_year_dir(parent.parent):
            return parent
    return None


def plans_for_directory(
    directory: Path,
    audio_format: str,
    legacy_transcribations: bool,
) -> list[ExtractionPlan]:
    if is_year_dir(directory):
        directory = directory / "videos"

    if directory.name != "videos":
        videos_dir = directory / "videos"
        if videos_dir.exists():
            directory = videos_dir

    return [
        ExtractionPlan(
            source=source,
            output=output_for_video(source, audio_format, legacy_transcribations),
        )
        for source in iter_video_files(directory)
    ]


def collect_plans(args: argparse.Namespace, repo: Path) -> list[ExtractionPlan]:
    plans: list[ExtractionPlan] = []

    for year_value in args.year_dir:
        year_dir = resolve_input(repo, year_value)
        plans.extend(plans_for_directory(year_dir, args.format, args.legacy_transcribations))

    if args.all_years:
        year_dirs = sorted(path for path in repo.iterdir() if is_year_dir(path))
        for year_dir in year_dirs:
            plans.extend(plans_for_directory(year_dir, args.format, args.legacy_transcribations))

    for input_value in args.inputs:
        path = resolve_input(repo, input_value)
        if path.is_file():
            if path.suffix.lower() not in VIDEO_EXTENSIONS:
                print(f"Skipping non-video file: {path}", file=sys.stderr)
                continue
            plans.append(
                ExtractionPlan(
                    path,
                    output_for_video(path, args.format, args.legacy_transcribations),
                )
            )
        elif path.is_dir():
            plans.extend(plans_for_directory(path, args.format, args.legacy_transcribations))
        else:
            raise SystemExit(f"Input does not exist: {path}")

    if not plans:
        raise SystemExit("No videos found. Pass a video file, --year-dir, or --all-years.")

    deduped: dict[Path, ExtractionPlan] = {}
    for plan in plans:
        deduped[plan.source] = plan
    return sorted(deduped.values(), key=lambda plan: str(plan.source))


def ffmpeg_audio_args(audio_format: str) -> list[str]:
    if audio_format == "m4a":
        return ["-c:a", "aac", "-b:a", "128k"]
    if audio_format == "mp3":
        return ["-c:a", "libmp3lame", "-q:a", "2"]
    if audio_format == "wav":
        return ["-c:a", "pcm_s16le"]
    raise ValueError(f"Unsupported format: {audio_format}")


def run_plan(plan: ExtractionPlan, audio_format: str, overwrite: bool) -> None:
    if plan.output.exists() and not overwrite:
        print(f"skip existing: {plan.output}")
        return

    plan.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if overwrite else "-n",
        "-i",
        str(plan.source),
        "-vn",
        *ffmpeg_audio_args(audio_format),
        str(plan.output),
    ]
    subprocess.run(command, check=True)
    print(f"wrote: {plan.output}")


def main() -> int:
    args = parse_args()
    repo = resolve_repo(args.repo)
    plans = collect_plans(args, repo)

    for plan in plans:
        print(f"{plan.source} -> {plan.output}")

    if args.dry_run:
        return 0

    needs_ffmpeg = args.overwrite or any(not plan.output.exists() for plan in plans)
    if needs_ffmpeg and shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg was not found on PATH; install ffmpeg before extracting audio.")

    for plan in plans:
        run_plan(plan, args.format, args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
