# src/preprocessing/resize_pad.py

import cv2
import numpy as np
from pathlib import Path


def load_rgb(path: Path) -> np.ndarray:
    """
    Load image from path as RGB numpy array.
    Uses np.fromfile + cv2.imdecode to avoid Unicode path issues.
    """
    path = Path(path)
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def resize_and_pad(img: np.ndarray, target_size: int = 1024,
                   pad_value=(255, 255, 255)):
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_h, new_w = int(h * scale), int(w * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    pad_top = (target_size - new_h) // 2
    pad_bottom = target_size - new_h - pad_top
    pad_left = (target_size - new_w) // 2
    pad_right = target_size - new_w - pad_left

    padded = cv2.copyMakeBorder(
        resized, pad_top, pad_bottom, pad_left, pad_right,
        cv2.BORDER_CONSTANT, value=pad_value
    )

    return padded, scale, pad_left, pad_top


def save_rgb(path: Path, img: np.ndarray):
    """
    Save an RGB image to disk, keeping the original filename exactly,
    and handling Unicode paths correctly on Windows.

    We use cv2.imencode + numpy.tofile instead of cv2.imwrite,
    which avoids OpenCV's filename encoding issues.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Choose extension from path; default to .png if missing
    ext = path.suffix or ".png"

    success, buf = cv2.imencode(ext, bgr)
    if not success:
        raise RuntimeError(f"Failed to encode image for saving: {path}")

    # Unicode-safe write
    buf.tofile(str(path))

