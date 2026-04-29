"""Core PDF → JPEG conversion logic."""

from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image
import io

SUPPORTED_INPUT = {".pdf"}

def _resolve_output_dir(
    input_path: Path,
    output_dir: Optional[Path],
    file_count: int,
) -> Path:
    """Single image → same folder as PDF; multiple → sub-folder named after the PDF."""
    if output_dir:
        dest = output_dir
    elif file_count > 1:
        dest = input_path.parent / input_path.stem
    else:
        dest = input_path.parent

    dest.mkdir(parents=True, exist_ok=True)
    return dest

def _apply_resize(
    img: Image.Image,
    width: Optional[int],
    height: Optional[int],
    max_size: Optional[int],
) -> Image.Image:
    orig_w, orig_h = img.size

    if max_size and (orig_w > max_size or orig_h > max_size):
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

def _save_jpeg(
    img: Image.Image,
    dest: Path,
    quality: int,
    strip_metadata: bool,
) -> int:
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    save_kwargs = {"format": "JPEG", "quality": quality}
    if strip_metadata:
        save_kwargs["exif"] = b""

    img.save(dest, **save_kwargs)
    return dest.stat().st_size

# ── Pages → JPEG ────────────────────────────────────────────────────────────

def render_pages(
    input_path: Path,
    output_dir: Optional[Path] = None,
    quality: int = 85,
    dpi: int = 200,
    page_range: Optional[Tuple[int, int]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_size: Optional[int] = None,
    strip_metadata: bool = True,
) -> List[Tuple[Path, int]]:
    """
    Render each PDF page to a JPEG file.

    Returns list of (output_path, output_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_INPUT:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    doc = fitz.open(input_path)
    total_pages = doc.page_count

    start, end = 0, total_pages
    if page_range:
        start = max(page_range[0] - 1, 0)
        end = min(page_range[1], total_pages)

    pages_to_render = list(range(start, end))
    dest = _resolve_output_dir(input_path, output_dir, len(pages_to_render))

    results: List[Tuple[Path, int]] = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for idx in pages_to_render:
        pix = doc[idx].get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img = _apply_resize(img, width, height, max_size)

        if len(pages_to_render) == 1:
            out_name = f"{input_path.stem}.jpg"
        else:
            out_name = f"{input_path.stem}_p{idx + 1:04d}.jpg"

        out_path = dest / out_name
        out_bytes = _save_jpeg(img, out_path, quality, strip_metadata)
        results.append((out_path, out_bytes))

    doc.close()
    return results

# ── Extract embedded images ──────────────────────────────────────────────────

def extract_images(
    input_path: Path,
    output_dir: Optional[Path] = None,
    quality: int = 85,
    min_width: int = 0,
    min_height: int = 0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_size: Optional[int] = None,
    strip_metadata: bool = True,
) -> List[Tuple[Path, int]]:
    """
    Extract embedded raster images from a PDF and save as JPEG.

    Returns list of (output_path, output_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_INPUT:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    doc = fitz.open(input_path)
    seen_xrefs: set = set()
    staged: List[Image.Image] = []

    for page_idx in range(doc.page_count):
        for img_info in doc[page_idx].get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            base_image = doc.extract_image(xref)
            if not base_image:
                continue

            img = Image.open(io.BytesIO(base_image["image"]))
            if img.width < min_width or img.height < min_height:
                continue

            staged.append(img)

    doc.close()

    if not staged:
        return []

    dest = _resolve_output_dir(input_path, output_dir, len(staged))
    results: List[Tuple[Path, int]] = []

    for i, img in enumerate(staged):
        img = _apply_resize(img, width, height, max_size)

        if len(staged) == 1:
            out_name = f"{input_path.stem}.jpg"
        else:
            out_name = f"{input_path.stem}_img{i + 1:04d}.jpg"

        out_path = dest / out_name
        out_bytes = _save_jpeg(img, out_path, quality, strip_metadata)
        results.append((out_path, out_bytes))

    return results