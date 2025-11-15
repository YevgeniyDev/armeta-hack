# src/tiling/tiler.py

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple


def load_rgb_unicode(path: Path) -> np.ndarray:
    """Unicode-safe image loader."""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def save_rgb_unicode(path: Path, img: np.ndarray):
    """Unicode-safe image writer."""
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ext = path.suffix or ".png"
    success, buf = cv2.imencode(ext, bgr)
    if not success:
        raise RuntimeError(f"Failed to encode image: {path}")
    buf.tofile(str(path))


def make_tiles(
    img: np.ndarray,
    tile_size: int = 1024,
    overlap_ratio: float = 0.20
) -> Tuple[List[np.ndarray], List[Tuple[int, int, int, int]]]:
    """
    Split an image into overlapping tiles WITHOUT resizing.
    Useful for high-resolution detection of small objects.

    Returns:
        tiles: list of tile images
        coords: list of (x0, y0, x1, y1) for each tile in parent image coords
    """
    h, w = img.shape[:2]

    stride = int(tile_size * (1 - overlap_ratio))
    if stride <= 0:
        raise ValueError("overlap_ratio too large — stride would be <= 0")

    tiles = []
    coords = []

    for y0 in range(0, h, stride):
        for x0 in range(0, w, stride):

            x1 = x0 + tile_size
            y1 = y0 + tile_size

            # clamp at image edges
            if x1 > w:
                x0 = w - tile_size
                x1 = w
            if y1 > h:
                y0 = h - tile_size
                y1 = h

            # skip if negative (happens for very small images)
            if x0 < 0 or y0 < 0:
                continue

            tile = img[y0:y1, x0:x1]

            # require exact tile_size
            if tile.shape[0] == tile_size and tile.shape[1] == tile_size:
                tiles.append(tile)
                coords.append((x0, y0, x1, y1))

    return tiles, coords


def tile_image_file(
    img_path: str | Path,
    out_dir: str | Path,
    tile_size: int = 1024,
    overlap_ratio: float = 0.20
):
    """
    High-level function:
    - loads image
    - generates tiles
    - saves tiles with unicode-safe names
    """
    img_path = Path(img_path)
    img = load_rgb_unicode(img_path)

    out_dir = Path(out_dir) / img_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    tiles, coords = make_tiles(img, tile_size, overlap_ratio)

    saved_files = []

    for idx, tile in enumerate(tiles):
        tile_name = f"{img_path.stem}_tile_{idx:03d}.png"
        tile_path = out_dir / tile_name
        save_rgb_unicode(tile_path, tile)
        saved_files.append(tile_path)

    return saved_files, coords


if __name__ == "__main__":
    # quick manual test
    test_img = Path("data/pngs_processed/АПЗ-2_page_001.png")
    out = Path("data/preprocessed/tiles")
    files, coords = tile_image_file(test_img, out, tile_size=1024, overlap_ratio=0.2)
    print("Saved:", files)
    print("Coords:", coords[:5])
