"""Core image conversion logic: PNG/JPG → WebP."""

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


SUPPORTED_INPUT = {".png", ".jpg", ".jpeg"}


def _resolve_output_path(input_path: Path, output_dir: Optional[Path]) -> Path:
    dest_dir = output_dir if output_dir else input_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / (input_path.stem + ".webp")


def _apply_resize(
    img: Image.Image,
    width: Optional[int],
    height: Optional[int],
    max_size: Optional[int],
) -> Image.Image:
    orig_w, orig_h = img.size

    if max_size and (orig_w > max_size or orig_h > max_size):
        # Proportional downscale so the longest edge equals max_size
        scale = max_size / max(orig_w, orig_h)
        width = int(orig_w * scale)
        height = int(orig_h * scale)

    if width and height:
        return img.resize((width, height), Image.LANCZOS)

    if width:
        ratio = width / orig_w
        return img.resize((width, int(orig_h * ratio)), Image.LANCZOS)

    if height:
        ratio = height / orig_h
        return img.resize((int(orig_w * ratio), height), Image.LANCZOS)

    return img


def convert(
    input_path: Path,
    output_dir: Optional[Path] = None,
    quality: int = 80,
    lossless: bool = False,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_size: Optional[int] = None,
    strip_metadata: bool = True,
) -> Tuple[Path, int, int]:
    """
    Convert a single image to WebP.

    Returns (output_path, original_bytes, output_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_INPUT:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    original_bytes = input_path.stat().st_size
    output_path = _resolve_output_path(input_path, output_dir)

    with Image.open(input_path) as img:
        # Preserve transparency only for RGBA sources
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        img = _apply_resize(img, width, height, max_size)

        save_kwargs = {
            "format": "WEBP",
            "quality": quality,
            "lossless": lossless,
            # method=6 is the slowest/best compression in Pillow's WebP encoder
            "method": 6,
        }

        # Strip Exif / XMP metadata unless caller explicitly wants to keep it
        if not strip_metadata:
            if hasattr(img, "info") and "exif" in img.info:
                save_kwargs["exif"] = img.info["exif"]

        img.save(output_path, **save_kwargs)

    output_bytes = output_path.stat().st_size
    return output_path, original_bytes, output_bytes
