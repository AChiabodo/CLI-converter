"""Typer CLI entry-point for rmbg."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .converter import remove_background, SUPPORTED_INPUT

app = typer.Typer(
    name="rmbg",
    help="Remove solid-color backgrounds from images, producing transparent PNGs.",
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

def _collect_images(paths: List[Path], recursive: bool) -> List[Path]:
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
                err_console.print(f"Skipped (unsupported): {p}")
    return collected

@app.command()
def remove(
    inputs: List[Path] = typer.Argument(
        ...,
        help="Image files or directories to process.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Destination directory. Default: same directory as each source file.",
    ),
    color: str = typer.Option(
        "#FFFFFF", "--color", "-c",
        help="Background color to remove. Accepts #RRGGBB or R,G,B (e.g. '#FFFFFF', '255,255,255').",
    ),
    tolerance: int = typer.Option(
        30, "--tolerance", "-t", min=0, max=442,
        help="Color distance threshold (0 = exact match, 442 = all colors). "
             "Higher values remove more shades around the target color.",
    ),
    feather: int = typer.Option(
        0, "--feather", "-f", min=0,
        help="Gaussian blur radius (px) applied to the alpha mask for soft edges.",
    ),
    invert: bool = typer.Option(
        False, "--invert",
        help="Invert selection: keep the background color, remove everything else.",
    ),
    edges_only: bool = typer.Option(
        False, "--edges-only", "-e",
        help="Remove only background regions connected to the image edges "
             "(flood-fill). Preserves interior regions of the same color.",
    ),
    crop: bool = typer.Option(
        False, "--crop",
        help="Trim fully-transparent borders from the output.",
    ),
    suffix: str = typer.Option(
        "_nobg", "--suffix", "-s",
        help="String appended to the output filename before .png extension.",
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
    """Remove a solid-color background from images, producing transparent PNGs."""

    files = _collect_images(inputs, recursive)

    if not files:
        err_console.print("No supported images found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(
            f"[bold yellow]Dry run — {len(files)} file(s) would be processed:[/bold yellow]"
        )
        for f in files:
            console.print(f"  {f}")
        raise typer.Exit()

    table = Table(
        title="Background Removal",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Input", style="dim")
    table.add_column("Output")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Δ", justify="right", style="bold green")

    errors: List[str] = []
    total_before = total_after = 0

    with console.status("[bold blue]Removing backgrounds…[/bold blue]", spinner="dots"):
        for file in files:
            try:
                out_path, before, after = remove_background(
                    input_path=file,
                    output_dir=output_dir,
                    color=color,
                    tolerance=tolerance,
                    feather=feather,
                    invert=invert,
                    edges_only=edges_only,
                    suffix=suffix,
                    crop=crop,
                )
                total_before += before
                total_after += after
                delta = ((after - before) / before * 100) if before else 0
                table.add_row(
                    str(file),
                    str(out_path),
                    _format_bytes(before),
                    _format_bytes(after),
                    f"{delta:+.1f}%",
                )
            except Exception as exc:
                errors.append(f"{file}: {exc}")

    console.print(table)

    if total_before:
        console.print(
            Panel(
                f"[bold]{len(files) - len(errors)}[/bold] file(s) processed — "
                f"target color: [bold]{color}[/bold] — "
                f"tolerance: [bold]{tolerance}[/bold]",
                border_style="cyan",
            )
        )

    if errors:
        err_console.print(f"\n{len(errors)} error(s):")
        for e in errors:
            err_console.print(f"  {e}")
        raise typer.Exit(code=1)