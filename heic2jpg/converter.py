"""Core image conversion logic: HEIC/HEIF → JPEG."""

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

SUPPORTED_INPUT = {".heic", ".heif"}

register_heif_opener()


def _resolve_output_path(input_path: Path, output_dir: Optional[Path]) -> Path:
    dest_dir = output_dir if output_dir else input_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{input_path.stem}.jpg"


def convert(
    input_path: Path,
    output_dir: Optional[Path] = None,
    quality: int = 92,
    strip_metadata: bool = True,
    overwrite: bool = False,
) -> Tuple[Path, int, int]:
    """
    Convert a single HEIC/HEIF image to JPEG.

    Returns (output_path, original_bytes, output_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_INPUT:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    original_bytes = input_path.stat().st_size
    output_path = _resolve_output_path(input_path, output_dir)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output_path}")

    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)
        rgb_img = img.convert("RGB")

        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
        }

        if not strip_metadata and "exif" in img.info:
            save_kwargs["exif"] = img.info["exif"]

        rgb_img.save(output_path, **save_kwargs)

    output_bytes = output_path.stat().st_size
    return output_path, original_bytes, output_bytes