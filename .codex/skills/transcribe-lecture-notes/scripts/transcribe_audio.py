from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_OPENAI_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_LANGUAGE = "ru"
DEFAULT_MAX_REQUEST_BYTES = 25 * 1024 * 1024
DEFAULT_CHUNK_SECONDS = 600
DEFAULT_SPLIT_BITRATE = "64k"
SPLIT_MODES = {"auto", "always", "never"}


@dataclass(frozen=True)
class Provider:
    name: str
    api_key: str
    model: str
    base_url: str | None


def die(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio with OpenAI or an OpenAI-compatible Audio API."
    )
    parser.add_argument("audio", nargs="+", help="Audio files to transcribe.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repository root. Used to load .env. Defaults to nearest parent with .git.",
    )
    parser.add_argument("--out", help="Output path for a single audio file.")
    parser.add_argument("--out-dir", help="Output directory for multiple transcripts.")
    parser.add_argument(
        "--language",
        default=None,
        help="Language hint. Defaults to LECTURE_TRANSCRIBE_LANGUAGE or ru.",
    )
    parser.add_argument(
        "--response-format",
        default="text",
        help="API response format. Use text for cleaned raw transcripts.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing transcript files.",
    )
    parser.add_argument(
        "--split-mode",
        choices=sorted(SPLIT_MODES),
        default="auto",
        help="Local ffmpeg splitting mode for large audio.",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=DEFAULT_CHUNK_SECONDS,
        help="Seconds per local ffmpeg chunk.",
    )
    parser.add_argument(
        "--split-bitrate",
        default=DEFAULT_SPLIT_BITRATE,
        help="Bitrate for local MP3 chunks.",
    )
    parser.add_argument(
        "--max-request-bytes",
        type=int,
        default=DEFAULT_MAX_REQUEST_BYTES,
        help="Split audio above this request size unless --split-mode never.",
    )
    parser.add_argument("--ffmpeg", help="Optional ffmpeg executable path.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve provider and output paths without calling the API.",
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


def resolve_repo(repo_arg: Path | None) -> Path:
    if repo_arg is not None:
        return repo_arg.resolve()
    return find_repo_root(Path.cwd())


def load_dotenv(repo: Path) -> dict[str, str]:
    env_path = repo / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def config_value(name: str, dotenv: dict[str, str]) -> str:
    return os.getenv(name) or dotenv.get(name, "")


def resolve_provider(dotenv: dict[str, str]) -> Provider:
    openai_key = config_value("OPENAI_API_KEY", dotenv)
    if openai_key:
        model = config_value("OPENAI_TRANSCRIBE_MODEL", dotenv) or DEFAULT_OPENAI_MODEL
        return Provider("openai", openai_key, model, None)

    compatible_key = config_value("OPENAI_COMPATIBLE_API_KEY", dotenv)
    compatible_base_url = config_value("OPENAI_COMPATIBLE_BASE_URL", dotenv)
    compatible_model = config_value("OPENAI_COMPATIBLE_TRANSCRIBE_MODEL", dotenv)
    if compatible_key and compatible_base_url and compatible_model:
        return Provider(
            "openai-compatible",
            compatible_key,
            compatible_model,
            compatible_base_url,
        )

    die(
        "No transcription provider configured. Set OPENAI_API_KEY, or set "
        "OPENAI_COMPATIBLE_API_KEY, OPENAI_COMPATIBLE_BASE_URL, and "
        "OPENAI_COMPATIBLE_TRANSCRIBE_MODEL in .env."
    )


def mask_key(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def resolve_audio(path_value: str, repo: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = repo / path
    path = path.resolve()
    if not path.exists():
        die(f"Audio file not found: {path}")
    if not path.is_file():
        die(f"Audio input is not a file: {path}")
    return path


def output_for_audio(audio_path: Path, args: argparse.Namespace, repo: Path) -> Path:
    if args.out:
        if len(args.audio) > 1:
            die("--out supports only one audio input.")
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = repo / out_path
        return out_path

    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = repo / out_dir
    else:
        out_dir = audio_path.parent
    return out_dir / f"{audio_path.stem}.transcript.txt"


def should_split(path: Path, args: argparse.Namespace) -> bool:
    if args.split_mode == "always":
        return True
    if args.split_mode == "never":
        return False
    return path.stat().st_size > args.max_request_bytes


def find_ffmpeg(args: argparse.Namespace) -> str:
    candidates = [args.ffmpeg, shutil.which("ffmpeg")]
    for candidate in candidates:
        if candidate:
            return candidate
    return ""


def split_audio(path: Path, args: argparse.Namespace, work_dir: Path) -> list[Path]:
    ffmpeg = find_ffmpeg(args)
    if not ffmpeg:
        die("ffmpeg was not found on PATH; install ffmpeg or pass --ffmpeg.")

    chunk_dir = work_dir / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    pattern = chunk_dir / "chunk_%03d.mp3"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-c:a",
        "libmp3lame",
        "-b:a",
        args.split_bitrate,
        "-f",
        "segment",
        "-segment_time",
        str(args.chunk_seconds),
        "-reset_timestamps",
        "1",
        str(pattern),
    ]
    subprocess.run(command, check=True)
    chunks = sorted(chunk_dir.glob("chunk_*.mp3"))
    if not chunks:
        die(f"ffmpeg produced no chunks for {path}")
    oversized = [
        chunk for chunk in chunks if chunk.stat().st_size > args.max_request_bytes
    ]
    if oversized:
        die("Generated chunks exceed the request size; reduce --chunk-seconds.")
    return chunks


def create_client(provider: Provider) -> Any:
    try:
        from openai import OpenAI
    except ImportError:
        die("openai package is not installed. Run with `uv run --with openai ...`.")

    if provider.base_url:
        return OpenAI(api_key=provider.api_key, base_url=provider.base_url)
    return OpenAI(api_key=provider.api_key)


def format_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
    return str(result)


def transcribe_one(client: Any, audio_path: Path, provider: Provider, args: argparse.Namespace) -> str:
    payload: dict[str, Any] = {
        "model": provider.model,
        "response_format": args.response_format,
    }
    if args.language:
        payload["language"] = args.language

    with audio_path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(file=audio_file, **payload)
    return format_result(result)


def transcribe_audio(client: Any, audio_path: Path, provider: Provider, args: argparse.Namespace) -> str:
    if not should_split(audio_path, args):
        return transcribe_one(client, audio_path, provider, args)

    with tempfile.TemporaryDirectory(prefix="lecture_transcribe_chunks_") as tmp_name:
        chunks = split_audio(audio_path, args, Path(tmp_name))
        outputs: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            print(f"Transcribing chunk {index}/{len(chunks)}: {chunk}", file=sys.stderr)
            outputs.append(transcribe_one(client, chunk, provider, args))
        return "\n\n".join(output.strip() for output in outputs if output.strip())


def main() -> int:
    args = parse_args()
    if args.chunk_seconds <= 0:
        die("--chunk-seconds must be positive.")
    if args.max_request_bytes <= 0:
        die("--max-request-bytes must be positive.")

    repo = resolve_repo(args.repo)
    dotenv = load_dotenv(repo)
    if args.language is None:
        args.language = config_value("LECTURE_TRANSCRIBE_LANGUAGE", dotenv) or DEFAULT_LANGUAGE

    provider = resolve_provider(dotenv)
    audio_paths = [resolve_audio(value, repo) for value in args.audio]
    output_paths = [output_for_audio(path, args, repo) for path in audio_paths]

    plan = {
        "provider": {
            "name": provider.name,
            "model": provider.model,
            "base_url": provider.base_url,
            "api_key": mask_key(provider.api_key),
        },
        "language": args.language,
        "items": [
            {
                "audio": str(audio),
                "output": str(output),
                "size": audio.stat().st_size,
                "split": should_split(audio, args),
            }
            for audio, output in zip(audio_paths, output_paths)
        ],
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    client = create_client(provider)
    for audio_path, output_path in zip(audio_paths, output_paths):
        if output_path.exists() and not args.overwrite:
            print(f"skip existing: {output_path}")
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        transcript = transcribe_audio(client, audio_path, provider, args)
        output_path.write_text(transcript, encoding="utf-8")
        print(f"wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
