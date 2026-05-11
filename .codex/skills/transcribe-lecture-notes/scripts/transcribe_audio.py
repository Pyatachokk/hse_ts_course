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


DEFAULT_MAX_REQUEST_BYTES = 25 * 1024 * 1024
DEFAULT_CHUNK_SECONDS = 600
DEFAULT_CIB_MAX_REQUEST_SECONDS = 3600
DEFAULT_SPLIT_BITRATE = "64k"
SPLIT_MODES = {"auto", "always", "never"}
CIB_PROVIDER_NAME = "cib-llm-api"
CIB_API_KEY_ENV_NAMES = ("CIB_LLM_API_KEY", "LLM_API_KEY")
CIB_BASE_URL_ENV_NAMES = ("CIB_LLM_BASE_URL", "LLM_API_BASE_URL")
CIB_MODEL_ENV_NAMES = ("CIB_LLM_TRANSCRIBE_MODEL", "LLM_TRANSCRIBE_MODEL")
CIB_MAX_SECONDS_ENV_NAMES = (
    "CIB_LLM_TRANSCRIBE_MAX_REQUEST_SECONDS",
    "LLM_TRANSCRIBE_MAX_REQUEST_SECONDS",
)
CIB_CHUNK_SECONDS_ENV_NAMES = (
    "CIB_LLM_TRANSCRIBE_CHUNK_SECONDS",
    "LLM_TRANSCRIBE_CHUNK_SECONDS",
)


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
        help="Repository root. Used to resolve relative paths. Defaults to nearest parent with .git.",
    )
    parser.add_argument("--out", help="Output path for a single audio file.")
    parser.add_argument("--out-dir", help="Output directory for multiple transcripts.")
    parser.add_argument(
        "--language",
        default=None,
        help="Language hint. Defaults to LECTURE_TRANSCRIBE_LANGUAGE from .env.",
    )
    parser.add_argument(
        "--response-format",
        default=None,
        help="API response format. Defaults to LECTURE_TRANSCRIBE_RESPONSE_FORMAT from .env.",
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
        default=None,
        help=(
            "Seconds per local ffmpeg chunk. Defaults to 600, or to the CIB "
            "duration limit when the CIB LLM API provider is selected."
        ),
    )
    parser.add_argument(
        "--split-bitrate",
        default=DEFAULT_SPLIT_BITRATE,
        help="Bitrate for local MP3 chunks.",
    )
    parser.add_argument(
        "--max-request-bytes",
        type=int,
        default=None,
        help=(
            "Split audio above this request size unless --split-mode never. "
            "Defaults to 25 MiB for non-CIB providers and is disabled for CIB LLM API."
        ),
    )
    parser.add_argument(
        "--cib-max-request-seconds",
        type=int,
        default=None,
        help=(
            "CIB LLM API maximum audio duration per transcription request. "
            "Defaults to 3600 seconds when the CIB provider is selected."
        ),
    )
    parser.add_argument(
        "--cib-chunk-seconds",
        type=int,
        default=None,
        help=(
            "Seconds per local ffmpeg chunk for CIB LLM API. Defaults to the "
            "CIB request duration limit."
        ),
    )
    parser.add_argument("--ffmpeg", help="Optional ffmpeg executable path.")
    parser.add_argument("--ffprobe", help="Optional ffprobe executable path.")
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


def config_value(name: str) -> str:
    return os.environ.get(name, "")


def first_config_value(names: tuple[str, ...]) -> str:
    for name in names:
        value = config_value(name)
        if value:
            return value
    return ""


def first_int_config_value(names: tuple[str, ...]) -> int | None:
    raw_value = first_config_value(names)
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        die(f"{', '.join(names)} must be an integer when set.")


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    audio_suffix = "/audio/transcriptions"
    if base_url.endswith(audio_suffix):
        return base_url[: -len(audio_suffix)].rstrip("/")
    return base_url


def require_config(name: str, provider_name: str) -> str:
    value = config_value(name)
    if not value:
        die(f"{provider_name} is selected but {name} is missing from the environment.")
    return value


def require_first_config(names: tuple[str, ...], provider_name: str) -> str:
    value = first_config_value(names)
    if not value:
        die(
            f"{provider_name} is selected but one of {', '.join(names)} is missing "
            "from the environment."
        )
    return value


def resolve_provider() -> Provider:
    openai_key = config_value("OPENAI_API_KEY")
    if openai_key:
        model = require_config("OPENAI_TRANSCRIBE_MODEL", "OpenAI")
        return Provider("openai", openai_key, model, None)

    cib_key = first_config_value(CIB_API_KEY_ENV_NAMES)
    if cib_key:
        cib_base_url = require_first_config(CIB_BASE_URL_ENV_NAMES, "CIB LLM API")
        cib_model = require_first_config(CIB_MODEL_ENV_NAMES, "CIB LLM API")
        return Provider(
            CIB_PROVIDER_NAME,
            cib_key,
            cib_model,
            normalize_base_url(cib_base_url),
        )

    compatible_key = config_value("OPENAI_COMPATIBLE_API_KEY")
    compatible_base_url = config_value("OPENAI_COMPATIBLE_BASE_URL")
    compatible_model = config_value("OPENAI_COMPATIBLE_TRANSCRIBE_MODEL")
    if compatible_key and compatible_base_url and compatible_model:
        return Provider(
            "openai-compatible",
            compatible_key,
            compatible_model,
            normalize_base_url(compatible_base_url),
        )

    die(
        "No transcription provider configured. Set OPENAI_API_KEY, set "
        "CIB_LLM_API_KEY for the CIB LLM API fallback, or set "
        "OPENAI_COMPATIBLE_API_KEY, OPENAI_COMPATIBLE_BASE_URL, and "
        "OPENAI_COMPATIBLE_TRANSCRIBE_MODEL for a custom compatible provider."
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


def apply_provider_defaults(args: argparse.Namespace, provider: Provider) -> None:
    if provider.name == CIB_PROVIDER_NAME:
        if args.cib_max_request_seconds is None:
            max_seconds = first_int_config_value(CIB_MAX_SECONDS_ENV_NAMES)
            args.cib_max_request_seconds = (
                max_seconds
                if max_seconds is not None
                else DEFAULT_CIB_MAX_REQUEST_SECONDS
            )
        if args.cib_chunk_seconds is None:
            chunk_seconds = first_int_config_value(CIB_CHUNK_SECONDS_ENV_NAMES)
            args.cib_chunk_seconds = (
                chunk_seconds
                if chunk_seconds is not None
                else args.cib_max_request_seconds
            )
        if args.chunk_seconds is None:
            args.chunk_seconds = args.cib_chunk_seconds
        return

    if args.chunk_seconds is None:
        args.chunk_seconds = DEFAULT_CHUNK_SECONDS
    if args.max_request_bytes is None:
        args.max_request_bytes = DEFAULT_MAX_REQUEST_BYTES


def validate_positive(value: int | None, option_name: str) -> None:
    if value is not None and value <= 0:
        die(f"{option_name} must be positive.")


def find_ffprobe(args: argparse.Namespace) -> str:
    candidates = [args.ffprobe]
    if args.ffmpeg:
        candidates.append(str(Path(args.ffmpeg).with_name("ffprobe")))
    candidates.append(shutil.which("ffprobe"))
    for candidate in candidates:
        if candidate:
            return candidate
    return ""


def audio_duration_seconds(path: Path, args: argparse.Namespace) -> float:
    ffprobe = find_ffprobe(args)
    if not ffprobe:
        die("ffprobe was not found on PATH; install ffprobe or pass --ffprobe.")

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        die(f"ffprobe failed for {path}: {result.stderr.strip()}")

    try:
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        die(f"Could not read audio duration from ffprobe output for {path}: {exc}")
    if duration <= 0:
        die(f"ffprobe returned a non-positive duration for {path}: {duration}")
    return duration


def cib_duration_limit(provider: Provider, args: argparse.Namespace) -> int | None:
    if provider.name != CIB_PROVIDER_NAME:
        return None
    return args.cib_max_request_seconds


def should_split(path: Path, provider: Provider, args: argparse.Namespace) -> bool:
    if args.split_mode == "always":
        return True
    if args.split_mode == "never":
        return False

    if (
        args.max_request_bytes is not None
        and path.stat().st_size > args.max_request_bytes
    ):
        return True

    duration_limit = cib_duration_limit(provider, args)
    if duration_limit is None:
        return False
    return audio_duration_seconds(path, args) > duration_limit


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
    oversized = (
        []
        if args.max_request_bytes is None
        else [chunk for chunk in chunks if chunk.stat().st_size > args.max_request_bytes]
    )
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
    payload: dict[str, Any] = {"model": provider.model}
    if args.response_format:
        payload["response_format"] = args.response_format
    if args.language:
        payload["language"] = args.language

    with audio_path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(file=audio_file, **payload)
    return format_result(result)


def transcribe_audio(client: Any, audio_path: Path, provider: Provider, args: argparse.Namespace) -> str:
    if not should_split(audio_path, provider, args):
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

    repo = resolve_repo(args.repo)
    if args.language is None:
        args.language = config_value("LECTURE_TRANSCRIBE_LANGUAGE") or None
    if args.response_format is None:
        args.response_format = config_value("LECTURE_TRANSCRIBE_RESPONSE_FORMAT") or None

    provider = resolve_provider()
    apply_provider_defaults(args, provider)
    validate_positive(args.chunk_seconds, "--chunk-seconds")
    validate_positive(args.max_request_bytes, "--max-request-bytes")
    validate_positive(args.cib_max_request_seconds, "--cib-max-request-seconds")
    validate_positive(args.cib_chunk_seconds, "--cib-chunk-seconds")

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
        "chunk_seconds": args.chunk_seconds,
        "max_request_bytes": args.max_request_bytes,
        "cib_max_request_seconds": cib_duration_limit(provider, args),
        "items": [
            {
                "audio": str(audio),
                "output": str(output),
                "size": audio.stat().st_size,
                "split": should_split(audio, provider, args),
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
