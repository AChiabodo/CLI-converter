"""Typer CLI entry-point for pdf2jpeg."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .converter import render_pages, extract_images, SUPPORTED_INPUT

app = typer.Typer(
    name="pdf2jpeg",
    help="Convert PDF files to JPEG — render pages or extract embedded images.",
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

def _print_results(
    results: List[tuple],
    pdf_path: Path,
    pdf_bytes: int,
    table: Table,
) -> int:
    total_out = 0
    for out_path, out_bytes in results:
        total_out += out_bytes
        table.add_row(
            str(pdf_path),
            str(out_path),
            _format_bytes(out_bytes),
        )
    return total_out

# ── Sub-command: pages ───────────────────────────────────────────────────────

@app.command()
def pages(
    inputs: List[Path] = typer.Argument(
        ...,
        help="PDF files or directories containing PDFs.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Destination directory. Default: sub-folder next to each PDF (multi-page) or same folder (single page).",
    ),
    quality: int = typer.Option(
        85, "--quality", "-q", min=1, max=100,
        help="JPEG quality (1–100).",
    ),
    dpi: int = typer.Option(
        200, "--dpi", "-d", min=36, max=600,
        help="Render resolution in DPI.",
    ),
    page_start: Optional[int] = typer.Option(
        None, "--from", "-f", min=1,
        help="First page to render (1-based).",
    ),
    page_end: Optional[int] = typer.Option(
        None, "--to", "-t", min=1,
        help="Last page to render (1-based, inclusive).",
    ),
    width: Optional[int] = typer.Option(
        None, "--width", "-W", min=1,
        help="Resize output to this width (preserves aspect ratio unless --height is also set).",
    ),
    height: Optional[int] = typer.Option(
        None, "--height", "-H", min=1,
        help="Resize output to this height (preserves aspect ratio unless --width is also set).",
    ),
    max_size: Optional[int] = typer.Option(
        None, "--max-size", "-m", min=1,
        help="Downscale so the longest edge ≤ this value (px). Overrides --width/--height.",
    ),
    strip_metadata: bool = typer.Option(
        True, "--strip-metadata/--keep-metadata",
        help="Strip Exif metadata (default: strip).",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r",
        help="Recurse into sub-directories.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="List files that would be processed without writing anything.",
    ),
) -> None:
    """Render each PDF page as a JPEG image."""

    pdfs = _collect_pdfs(inputs, recursive)
    if not pdfs:
        err_console.print("No PDF files found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(
            f"[bold yellow]Dry run — {len(pdfs)} PDF(s) would be processed:[/bold yellow]"
        )
        for f in pdfs:
            console.print(f"  {f}")
        raise typer.Exit()

    page_range = None
    if page_start or page_end:
        page_range = (page_start or 1, page_end or 999_999)

    table = Table(
        title="PDF → JPEG  (pages)",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Source PDF", style="dim")
    table.add_column("Output")
    table.add_column("Size", justify="right")

    errors: List[str] = []
    total_images = 0
    total_bytes = 0

    with console.status("[bold blue]Rendering pages…[/bold blue]", spinner="dots"):
        for pdf in pdfs:
            try:
                results = render_pages(
                    input_path=pdf,
                    output_dir=output_dir,
                    quality=quality,
                    dpi=dpi,
                    page_range=page_range,
                    width=width,
                    height=height,
                    max_size=max_size,
                    strip_metadata=strip_metadata,
                )
                total_bytes += _print_results(
                    results, pdf, pdf.stat().st_size, table,
                )
                total_images += len(results)
            except Exception as exc:
                errors.append(f"{pdf}: {exc}")

    console.print(table)
    console.print(
        Panel(
            f"[bold]{total_images}[/bold] image(s) generated — "
            f"total output size: [bold green]{_format_bytes(total_bytes)}[/bold green]",
            border_style="cyan",
        )
    )

    if errors:
        err_console.print(f"\n{len(errors)} error(s):")
        for e in errors:
            err_console.print(f"  {e}")
        raise typer.Exit(code=1)

# ── Sub-command: extract ─────────────────────────────────────────────────────

@app.command()
def extract(
    inputs: List[Path] = typer.Argument(
        ...,
        help="PDF files or directories containing PDFs.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Destination directory. Default: sub-folder next to each PDF (multi-image) or same folder (single image).",
    ),
    quality: int = typer.Option(
        85, "--quality", "-q", min=1, max=100,
        help="JPEG quality (1–100).",
    ),
    min_width: int = typer.Option(
        0, "--min-width", min=0,
        help="Skip embedded images narrower than this (px).",
    ),
    min_height: int = typer.Option(
        0, "--min-height", min=0,
        help="Skip embedded images shorter than this (px).",
    ),
    width: Optional[int] = typer.Option(
        None, "--width", "-W", min=1,
        help="Resize output to this width (preserves aspect ratio unless --height is also set).",
    ),
    height: Optional[int] = typer.Option(
        None, "--height", "-H", min=1,
        help="Resize output to this height (preserves aspect ratio unless --width is also set).",
    ),
    max_size: Optional[int] = typer.Option(
        None, "--max-size", "-m", min=1,
        help="Downscale so the longest edge ≤ this value (px). Overrides --width/--height.",
    ),
    strip_metadata: bool = typer.Option(
        True, "--strip-metadata/--keep-metadata",
        help="Strip Exif metadata (default: strip).",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r",
        help="Recurse into sub-directories.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="List files that would be processed without writing anything.",
    ),
) -> None:
    """Extract embedded raster images from PDFs and save as JPEG."""

    pdfs = _collect_pdfs(inputs, recursive)
    if not pdfs:
        err_console.print("No PDF files found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(
            f"[bold yellow]Dry run — {len(pdfs)} PDF(s) would be scanned:[/bold yellow]"
        )
        for f in pdfs:
            console.print(f"  {f}")
        raise typer.Exit()

    table = Table(
        title="PDF → JPEG  (extract images)",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Source PDF", style="dim")
    table.add_column("Output")
    table.add_column("Size", justify="right")

    errors: List[str] = []
    total_images = 0
    total_bytes = 0

    with console.status(
        "[bold blue]Extracting images…[/bold blue]", spinner="dots"
    ):
        for pdf in pdfs:
            try:
                results = extract_images(
                    input_path=pdf,
                    output_dir=output_dir,
                    quality=quality,
                    min_width=min_width,
                    min_height=min_height,
                    width=width,
                    height=height,
                    max_size=max_size,
                    strip_metadata=strip_metadata,
                )
                if not results:
                    console.print(
                        f"  [dim]No images found in {pdf}[/dim]"
                    )
                    continue
                total_bytes += _print_results(
                    results, pdf, pdf.stat().st_size, table,
                )
                total_images += len(results)
            except Exception as exc:
                errors.append(f"{pdf}: {exc}")

    console.print(table)
    console.print(
        Panel(
            f"[bold]{total_images}[/bold] image(s) extracted — "
            f"total output size: [bold green]{_format_bytes(total_bytes)}[/bold green]",
            border_style="cyan",
        )
    )

    if errors:
        err_console.print(f"\n{len(errors)} error(s):")
        for e in errors:
            err_console.print(f"  {e}")
        raise typer.Exit(code=1)