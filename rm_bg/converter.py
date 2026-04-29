"""Core background removal logic: color-based → transparent PNG."""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter

SUPPORTED_INPUT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}

def _resolve_output_path(
    input_path: Path,
    output_dir: Optional[Path],
    suffix: str = "_nobg",
) -> Path:
    dest_dir = output_dir if output_dir else input_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{input_path.stem}{suffix}.png"

def _parse_color(color: str) -> Tuple[int, int, int]:
    """Accept hex (#RRGGBB / RRGGBB) or comma-separated R,G,B."""
    color = color.strip().lstrip("#")

    if "," in color:
        parts = [int(c.strip()) for c in color.split(",")]
        if len(parts) != 3 or not all(0 <= c <= 255 for c in parts):
            raise ValueError(f"Invalid RGB: {color}")
        return (parts[0], parts[1], parts[2])

    if len(color) == 6:
        return (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

    raise ValueError(
        f"Cannot parse color '{color}'. Use #RRGGBB or R,G,B format."
    )

def _color_distance(pixels: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Euclidean distance in RGB space between each pixel and the target color."""
    return np.sqrt(np.sum((pixels.astype(np.float64) - target.astype(np.float64)) ** 2, axis=-1))

def remove_background(
    input_path: Path,
    output_dir: Optional[Path] = None,
    color: str = "#FFFFFF",
    tolerance: int = 30,
    feather: int = 0,
    invert: bool = False,
    edges_only: bool = False,
    suffix: str = "_nobg",
    crop: bool = False,
) -> Tuple[Path, int, int]:
    """
    Remove a solid-color background from an image, producing a transparent PNG.

    Parameters
    ----------
    input_path : source image
    output_dir : destination folder (default: same as source)
    color      : background color to remove (#RRGGBB or R,G,B)
    tolerance  : max Euclidean distance in RGB space to still consider a pixel
                 as "background" (0 = exact match only, 442 = everything)
    feather    : gaussian-blur radius applied to the alpha mask for soft edges (px)
    invert     : if True, keep the background and remove the foreground
    edges_only : remove background only for pixels connected to image edges
                 (flood-fill approach — preserves interior regions of the same color)
    suffix     : string appended to the output filename
    crop       : trim fully-transparent borders from the result

    Returns (output_path, original_bytes, output_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_INPUT:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    original_bytes = input_path.stat().st_size
    output_path = _resolve_output_path(input_path, output_dir, suffix)

    target_rgb = np.array(_parse_color(color), dtype=np.float64)

    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        data = np.array(img)

        rgb = data[:, :, :3]
        dist = _color_distance(rgb, target_rgb)

        # Boolean mask: True = pixel is "background"
        bg_mask = dist <= tolerance

        if edges_only:
            bg_mask = _flood_fill_edges(bg_mask)

        if invert:
            bg_mask = ~bg_mask

        # Build alpha channel: 0 where background, 255 where foreground
        alpha = np.where(bg_mask, 0, 255).astype(np.uint8)

        if feather > 0:
            alpha_img = Image.fromarray(alpha, mode="L")
            alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=feather))
            alpha = np.array(alpha_img)

        data[:, :, 3] = alpha
        result = Image.fromarray(data, "RGBA")

        if crop:
            bbox = result.getbbox()
            if bbox:
                result = result.crop(bbox)

        result.save(output_path, format="PNG", optimize=True)

    output_bytes = output_path.stat().st_size
    return output_path, original_bytes, output_bytes

def _flood_fill_edges(mask: np.ndarray) -> np.ndarray:
    """
    Starting from image edges, flood-fill through True pixels.
    Only edge-connected background regions are marked; interior
    regions of the same color are preserved.
    """
    from scipy.ndimage import label

    # Fast-path: no background pixels to propagate.
    if not np.any(mask):
        return np.zeros_like(mask, dtype=bool)

    # Explicit 4-connectivity to match the previous iterative dilation behavior.
    structure = np.array(
        [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0],
        ],
        dtype=np.uint8,
    )
    labeled, _ = label(mask, structure=structure)

    edge_labels = np.unique(
        np.concatenate(
            [
                labeled[0, :],
                labeled[-1, :],
                labeled[:, 0],
                labeled[:, -1],
            ]
        )
    )
    edge_labels = edge_labels[edge_labels != 0]

    # Fast-path: no labeled component touches the borders.
    if edge_labels.size == 0:
        return np.zeros_like(mask, dtype=bool)

    return np.isin(labeled, edge_labels)
