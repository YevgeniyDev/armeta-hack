# src/preprocessing/resize_pad.py

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple


def load_rgb(path: Path) -> np.ndarray:
    """
    Load image from path as RGB numpy array.
    """
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def resize_and_pad(
    img: np.ndarray,
    target_size: int = 1024,
    pad_value: Tuple[int, int, int] = (255, 255, 255)
) -> Tuple[np.ndarray, float, int, int]:
    """
    Resize image keeping aspect ratio, then pad to square (target_size x target_size).

    Returns:
        padded_img: resized and padded image
        scale: scaling factor applied to original image
        pad_left: number of pixels padded on the left
        pad_top: number of pixels padded on the top
    """
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_h, new_w = int(h * scale), int(w * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Compute padding to center the resized image
    pad_top = (target_size - new_h) // 2
    pad_bottom = target_size - new_h - pad_top
    pad_left = (target_size - new_w) // 2
    pad_right = target_size - new_w - pad_left

    padded = cv2.copyMakeBorder(
        resized,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_CONSTANT,
        value=pad_value
    )

    return padded, scale, pad_left, pad_top


def save_rgb(path: Path, img: np.ndarray):
    """
    Save an RGB numpy array as an image to disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), bgr)
