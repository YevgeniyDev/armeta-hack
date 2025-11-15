# src/tiling/tiler.py

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple


def load_rgb(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def save_rgb(path: Path, img: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), bgr)


def make_tiles(
    img: np.ndarray,
    tile_size: int = 1024,
    overlap_ratio: float = 0.2
) -> Tuple[List[np.ndarray], List[Tuple[int, int, int, int]]]:
    """
    Split image into overlapping tiles.

    Args:
        img: RGB image (H, W, 3)
        tile_size: tile side length in pixels
        overlap_ratio: fraction of tile size that overlaps with neighbors

    Returns:
        tiles: list of tile images (each tile_size x tile_size)
        coords: list of (x0, y0, x1, y1) for each tile in original image coordinates
    """
    h, w = img.shape[:2]
    tiles = []
    coords = []

    stride = int(tile_size * (1 - overlap_ratio))
    if stride <= 0:
        raise ValueError("overlap_ratio too large, stride <= 0")

    for y0 in range(0, max(h - tile_size + 1, 1), stride):
        for x0 in range(0, max(w - tile_size + 1, 1), stride):
            x1 = min(x0 + tile_size, w)
            y1 = min(y0 + tile_size, h)

            # Shift window if at right/bottom border to keep full tile_size
            x0 = max(x1 - tile_size, 0)
            y0 = max(y1 - tile_size, 0)

            tile = img[y0:y1, x0:x1]
            if tile.shape[0] == tile_size and tile.shape[1] == tile_size:
                tiles.append(tile)
                coords.append((x0, y0, x1, y1))

    return tiles, coords


def tile_all_preprocessed(
    src_dir: str = "data/preprocessed/train",
    dst_dir: str = "data/tiles/train",
    tile_size: int = 1024,
    overlap_ratio: float = 0.2
):
    """
    Generate tiles for all preprocessed images for inspection / optional tile-based training.
    """
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(src_dir.glob("*.png"))

    for img_path in image_paths:
        img = load_rgb(img_path)
        tiles, coords = make_tiles(img, tile_size=tile_size, overlap_ratio=overlap_ratio)

        base_name = img_path.stem
        for i, tile in enumerate(tiles):
            tile_name = f"{base_name}_tile_{i:02d}.png"
            tile_path = dst_dir / tile_name
            save_rgb(tile_path, tile)

        # For now, just printing. You could also save coords to a JSON for later use.
        print(f"[TILER] {img_path.name}: {len(tiles)} tiles")


if __name__ == "__main__":
    tile_all_preprocessed()
