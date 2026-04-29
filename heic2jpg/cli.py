"""Typer CLI entry-point for heic2jpg."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from .converter import convert, SUPPORTED_INPUT

app = typer.Typer(
    name="heic2jpg",
    help="Convert HEIC/HEIF images to JPEG format.",
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


def _collect_inputs(paths: List[Path], recursive: bool) -> List[Path]:
    """Expand directories and filter by supported extensions."""
    collected: List[Path] = []
    for p in paths:
        if p.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in sorted(p.glob(pattern)):
                if child.is_file() and child.suffix.lower() in SUPPORTED_INPUT:
                    collected.append(child)
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED_INPUT:
                collected.append(p)
            else:
                err_console.print(f"Skipped (unsupported format): {p}")
    return collected


@app.command()
def convert_images(
    inputs: List[Path] = typer.Argument(
        ...,
        help="Input files or directories (HEIC/HEIF).",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination directory. Defaults to same directory as each source file.",
    ),
    quality: int = typer.Option(
        92,
        "--quality",
        "-q",
        min=1,
        max=100,
        help="JPEG quality (1–100).",
    ),
    strip_metadata: bool = typer.Option(
        True,
        "--strip-metadata/--keep-metadata",
        help="Strip Exif metadata (default: strip).",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Recurse into sub-directories when a directory is given as input.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing JPEG files.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be converted without writing any files.",
    ),
) -> None:
    """Convert HEIC/HEIF images to JPEG."""

    files = _collect_inputs(inputs, recursive)

    if not files:
        err_console.print("No supported images found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(f"[bold yellow]Dry run — {len(files)} file(s) would be processed:[/bold yellow]")
        for f in files:
            console.print(f"  {f}")
        raise typer.Exit()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Input", style="dim")
    table.add_column("Output")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Saving", justify="right", style="bold green")

    errors: List[str] = []
    total_before = 0
    total_after = 0

    with console.status("[bold blue]Converting…[/bold blue]", spinner="dots"):
        for file in files:
            try:
                out_path, before, after = convert(
                    input_path=file,
                    output_dir=output_dir,
                    quality=quality,
                    strip_metadata=strip_metadata,
                    overwrite=overwrite,
                )
                total_before += before
                total_after += after
                saving_pct = (1 - after / before) * 100 if before else 0

                table.add_row(
                    str(file),
                    str(out_path),
                    _format_bytes(before),
                    _format_bytes(after),
                    f"{saving_pct:+.1f}%",
                )
            except Exception as exc:
                errors.append(f"{file}: {exc}")

    console.print(table)

    if total_before:
        overall_saving = (1 - total_after / total_before) * 100
        console.print(
            f"[bold]Total:[/bold] {_format_bytes(total_before)} → {_format_bytes(total_after)} "
            f"([bold green]{overall_saving:+.1f}%[/bold green] overall)"
        )

    if errors:
        err_console.print(f"\n{len(errors)} error(s):")
        for e in errors:
            err_console.print(f"  {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()