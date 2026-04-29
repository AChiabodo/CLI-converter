"""Core PDF compression logic."""

from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF


SUPPORTED_INPUT = {".pdf"}


def _resolve_output_path(input_path: Path, output_dir: Optional[Path]) -> Path:
    dest_dir = output_dir if output_dir else input_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{input_path.stem}_compressed.pdf"


def compress(
    input_path: Path,
    output_dir: Optional[Path] = None,
    quality: int = 75,
    overwrite: bool = False,
) -> Tuple[Path, int, int]:
    """
    Compress a single PDF file.

    Returns (output_path, original_bytes, output_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_INPUT:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    original_bytes = input_path.stat().st_size
    output_path = _resolve_output_path(input_path, output_dir)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output_path}")

    doc = fitz.open(input_path)
    try:
        # Recompress embedded images using the requested JPEG quality.
        doc.rewrite_images(quality=quality)

        # Save with aggressive cleanup and stream compression.
        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            use_objstms=1,
            compression_effort=100,
        )
    finally:
        doc.close()

    output_bytes = output_path.stat().st_size
    return output_path, original_bytes, output_bytes

