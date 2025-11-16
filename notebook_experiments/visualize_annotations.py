# notebook_experiments/visualize_annotations_raw.py

import os
import sys
import json
from pathlib import Path

import numpy as np
import cv2

# -------------------------------------------------------------------
# Ensure we can import project modules (if needed)
# -------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- Unicode-safe image IO (works with Cyrillic paths) ----------
def load_rgb_unicode(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def save_rgb_unicode(path: Path, img_rgb: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    ext = path.suffix or ".png"
    ok, buf = cv2.imencode(ext, bgr)
    if not ok:
        raise RuntimeError(f"Failed to encode image for: {path}")
    buf.tofile(str(path))


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
ANNOT_PATH = "outputs/selected_annotations.json"   # your annotation JSON
RAW_IMAGES_DIR = Path("data/pngs_processed")       # original PNGs from pdf_to_images.py
OUT_DIR = Path("outputs/annotation_preview_raw")

CLASS_COLORS = {
    "signature": (0, 255, 0),   # green
    "stamp": (255, 0, 0),       # blue-ish
    "qr": (0, 0, 255),          # red
}


def draw_boxes(img_rgb, boxes):
    """boxes: list of (class_name, (x, y, w, h)) in *PNG pixel coords*"""
    out = img_rgb.copy()
    for cls, (x, y, w, h) in boxes:
        color = CLASS_COLORS.get(cls, (255, 255, 255))
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + w), int(y + h)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)
        cv2.putText(
            out,
            cls,
            (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2,
            cv2.LINE_AA,
        )
    return out


def visualize():
    print("[VIS] Loading annotations...")
    with open(ANNOT_PATH, "r", encoding="utf-8") as f:
        ann = json.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # iterate over all original PNG pages
    for img_path in RAW_IMAGES_DIR.glob("*.png"):
        filename = img_path.name          # "АПЗ-2_page_001.png"
        stem = img_path.stem

        # parse "<pdfname>_page_<num>"
        try:
            pdf_name, page_str = stem.rsplit("_page_", 1)
            page_idx = int(page_str)
            page_key = f"page_{page_idx}"        # "page_1"
            pdf_key = pdf_name + ".pdf"          # "АПЗ-2.pdf"
        except ValueError:
            print(f"[WARN] Cannot parse pdf/page from {filename}")
            continue

        if pdf_key not in ann or page_key not in ann[pdf_key]:
            continue

        page_data = ann[pdf_key][page_key]
        page_ann = page_data.get("annotations", [])
        page_size = page_data.get("page_size", None)

        # load PNG image
        try:
            img_rgb = load_rgb_unicode(img_path)
        except FileNotFoundError as e:
            print("[ERROR]", e)
            continue

        h_img, w_img = img_rgb.shape[:2]

        # if page_size exists, use it to scale bbox → PNG coords
        if page_size is not None:
            page_w = float(page_size["width"])
            page_h = float(page_size["height"])
            sx = w_img / page_w
            sy = h_img / page_h
        else:
            # fallback: assume same coordinate system (no scaling)
            sx = sy = 1.0

        boxes = []
        for item in page_ann:
            ann_id, entry = next(iter(item.items()))
            cls = entry["category"]
            bbox = entry["bbox"]

            # coords in PDF/page space
            x = bbox["x"]
            y = bbox["y"]
            w = bbox["width"]
            h = bbox["height"]

            # scale to PNG coordinates
            x_png = x * sx
            y_png = y * sy
            w_png = w * sx
            h_png = h * sy

            boxes.append((cls, (x_png, y_png, w_png, h_png)))

        vis = draw_boxes(img_rgb, boxes)

        out_dir = OUT_DIR / pdf_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{stem}_vis.png"

        save_rgb_unicode(out_path, vis)
        print("[VIS] Saved", out_path)


if __name__ == "__main__":
    visualize()
