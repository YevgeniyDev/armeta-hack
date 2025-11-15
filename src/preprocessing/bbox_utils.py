from typing import Tuple


def convert_orig_to_preprocessed(x, y, w, h, meta):
    """
    Convert bbox from original PDF coordinates → preprocessed 1024×1024.

    meta = {
      "scale": float,
      "pad_left": int,
      "pad_top": int,
      "orig_width": int,
      "orig_height": int,
      "target_size": 1024
    }
    """
    s = meta["scale"]
    pl = meta["pad_left"]
    pt = meta["pad_top"]

    # Scale + pad 
    x_p = x * s + pl
    y_p = y * s + pt
    w_p = w * s
    h_p = h * s

    return x_p, y_p, w_p, h_p


def clip_bbox(x, y, w, h, size=1024):
    """
    Keep bbox inside 1024×1024 borders.
    """
    x = max(0, min(x, size - 1))
    y = max(0, min(y, size - 1))
    w = max(1, min(w, size - x))
    h = max(1, min(h, size - y))
    return x, y, w, h


def xywh_to_yolo(x, y, w, h, size=1024):
    """
    Convert xywh absolute to YOLO normalized format.
    """
    xc = (x + w / 2) / size
    yc = (y + h / 2) / size
    wn = w / size
    hn = h / size
    return xc, yc, wn, hn
