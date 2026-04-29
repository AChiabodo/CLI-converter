"""Typer CLI entry-point for vid2audio."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .converter import (
    extract_audio,
    get_audio_info,
    SUPPORTED_VIDEO,
    AUDIO_CODECS,
)

app = typer.Typer(
    name="vid2audio",
    help="Extract audio from video files (MP4, MKV, AVI, MOV, WebM …).",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True, style="bold red")

def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def _collect_videos(paths: List[Path], recursive: bool) -> List[Path]:
    collected: List[Path] = []
    for p in paths:
        if p.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in sorted(p.glob(pattern)):
                if child.is_file() and child.suffix.lower() in SUPPORTED_VIDEO:
                    collected.append(child)
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED_VIDEO:
                collected.append(p)
            else:
                err_console.print(f"Skipped (unsupported): {p}")
    return collected

# ── Sub-command: extract ─────────────────────────────────────────────────────

@app.command()
def extract(
    inputs: List[Path] = typer.Argument(
        ...,
        help="Video files or directories to process.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Destination directory. Default: same directory as each source video.",
    ),
    audio_format: str = typer.Option(
        "mp3", "--format", "-f",
        help="Output audio format: mp3, aac, opus, flac, wav, ogg, copy (stream copy).",
    ),
    bitrate: Optional[str] = typer.Option(
        None, "--bitrate", "-b",
        help="Audio bitrate (e.g. 192k, 320k). Ignored with --format copy.",
    ),
    sample_rate: Optional[int] = typer.Option(
        None, "--sample-rate", "-s",
        help="Audio sample rate in Hz (e.g. 44100, 48000). Ignored with --format copy.",
    ),
    channels: Optional[int] = typer.Option(
        None, "--channels", "-c", min=1, max=8,
        help="Number of audio channels (1 = mono, 2 = stereo). Ignored with --format copy.",
    ),
    volume: Optional[float] = typer.Option(
        None, "--volume", "-v",
        help="Volume multiplier (e.g. 1.5 = +50%%, 0.5 = -50%%). Ignored with --format copy.",
    ),
    start: Optional[str] = typer.Option(
        None, "--start", "-ss",
        help="Start time offset (HH:MM:SS or seconds).",
    ),
    duration: Optional[str] = typer.Option(
        None, "--duration", "-t",
        help="Duration to extract (HH:MM:SS or seconds).",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", "-y",
        help="Overwrite existing output files.",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r",
        help="Recurse into sub-directories.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be processed without writing any files.",
    ),
) -> None:
    """Extract audio tracks from video files."""

    if audio_format not in AUDIO_CODECS:
        err_console.print(
            f"Unknown format '{audio_format}'. "
            f"Supported: {', '.join(AUDIO_CODECS)}"
        )
        raise typer.Exit(code=1)

    files = _collect_videos(inputs, recursive)

    if not files:
        err_console.print("No supported video files found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(
            f"[bold yellow]Dry run — {len(files)} file(s) would be processed:[/bold yellow]"
        )
        for f in files:
            console.print(f"  {f}")
        raise typer.Exit()

    table = Table(
        title="Video → Audio",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Input", style="dim")
    table.add_column("Output")
    table.add_column("Video size", justify="right")
    table.add_column("Audio size", justify="right")
    table.add_column("Ratio", justify="right", style="bold green")

    errors: List[str] = []
    total_video = total_audio = 0

    with console.status("[bold blue]Extracting audio…[/bold blue]", spinner="dots"):
        for file in files:
            try:
                out_path, v_bytes, a_bytes = extract_audio(
                    input_path=file,
                    output_dir=output_dir,
                    audio_format=audio_format,
                    bitrate=bitrate,
                    sample_rate=sample_rate,
                    channels=channels,
                    volume=volume,
                    start=start,
                    duration=duration,
                    overwrite=overwrite,
                )
                total_video += v_bytes
                total_audio += a_bytes
                ratio = (a_bytes / v_bytes * 100) if v_bytes else 0
                table.add_row(
                    str(file),
                    str(out_path),
                    _format_bytes(v_bytes),
                    _format_bytes(a_bytes),
                    f"{ratio:.1f}%",
                )
            except Exception as exc:
                errors.append(f"{file}: {exc}")

    console.print(table)

    if total_video:
        overall_ratio = total_audio / total_video * 100
        console.print(
            Panel(
                f"[bold]{len(files) - len(errors)}[/bold] file(s) processed — "
                f"{_format_bytes(total_video)} video → "
                f"[bold green]{_format_bytes(total_audio)}[/bold green] audio "
                f"([bold green]{overall_ratio:.1f}%[/bold green] of original)",
                border_style="cyan",
            )
        )

    if errors:
        err_console.print(f"\n{len(errors)} error(s):")
        for e in errors:
            err_console.print(f"  {e}")
        raise typer.Exit(code=1)

# ── Sub-command: info ────────────────────────────────────────────────────────

@app.command()
def info(
    inputs: List[Path] = typer.Argument(
        ...,
        help="Video files to inspect.",
        exists=True,
        readable=True,
    ),
) -> None:
    """Show audio stream metadata for video files."""

    table = Table(
        title="Audio stream info",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("File", style="dim")
    table.add_column("Codec")
    table.add_column("Sample rate")
    table.add_column("Channels", justify="center")
    table.add_column("Bitrate", justify="right")
    table.add_column("Duration", justify="right")

    for f in inputs:
        try:
            meta = get_audio_info(f)
            br = meta.get("bitrate")
            br_str = _format_bytes(int(br)) + "/s" if br else "—"
            dur = meta.get("duration")
            dur_str = f"{float(dur):.1f}s" if dur else "—"
            table.add_row(
                str(f),
                meta.get("codec") or "—",
                f"{meta.get('sample_rate') or '—'} Hz",
                str(meta.get("channels") or "—"),
                br_str,
                dur_str,
            )
        except Exception as exc:
            table.add_row(str(f), f"[red]{exc}[/red]", "", "", "", "")

    console.print(table)