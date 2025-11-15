# src/tiling/tile_utils.py

from typing import Tuple


def tile_box_to_full(
    box_xyxy: Tuple[float, float, float, float],
    tile_coords: Tuple[int, int, int, int]
) -> Tuple[float, float, float, float]:
    """
    Convert a box predicted on a tile into full-image coordinates.
    tile_coords = (x0, y0, x1, y1) of tile in full image.
    """
    x0_tile, y0_tile, _, _ = tile_coords
    x1, y1, x2, y2 = box_xyxy

    return (
        x1 + x0_tile,
        y1 + y0_tile,
        x2 + x0_tile,
        y2 + y0_tile
    )
