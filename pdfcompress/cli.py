"""Typer CLI entry-point for pdfcompress."""

from pathlib import Path
from typing import List, Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from .converter import SUPPORTED_INPUT, compress

app = typer.Typer(
    name="pdfcompress",
    help="Compress PDF files with selectable image quality.",
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


def _collect_pdfs(paths: List[Path], recursive: bool) -> List[Path]:
    collected: List[Path] = []
    for p in paths:
        if p.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            for child in sorted(p.glob(pattern)):
                if child.is_file():
                    collected.append(child)
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED_INPUT:
                collected.append(p)
            else:
                err_console.print(f"Skipped (not a PDF): {p}")
    return collected


@app.command()
def compress_pdfs(
    inputs: List[Path] = typer.Argument(
        ...,
        help="Input PDF files or directories containing PDFs.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination directory. Default: same folder as each source file.",
    ),
    quality: int = typer.Option(
        75,
        "--quality",
        "-q",
        min=1,
        max=100,
        help="Compression quality for embedded images (1-100). Lower = smaller files.",
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
        help="Overwrite existing compressed PDF files.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be compressed without writing files.",
    ),
) -> None:
    """Compress one or more PDF files."""

    files = _collect_pdfs(inputs, recursive)
    if not files:
        err_console.print("No PDF files found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(
            f"[bold yellow]Dry run - {len(files)} file(s) would be processed:[/bold yellow]"
        )
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

    with console.status("[bold blue]Compressing PDFs...[/bold blue]", spinner="dots"):
        for file in files:
            try:
                out_path, before, after = compress(
                    input_path=file,
                    output_dir=output_dir,
                    quality=quality,
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
            f"[bold]Total:[/bold] {_format_bytes(total_before)} -> {_format_bytes(total_after)} "
            f"([bold green]{overall_saving:+.1f}%[/bold green] overall)"
        )

    if errors:
        err_console.print(f"\n{len(errors)} error(s):")
        for e in errors:
            err_console.print(f"  {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

