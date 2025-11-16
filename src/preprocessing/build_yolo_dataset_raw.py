import os
import sys
import json
import shutil
import random
from pathlib import Path
from collections import Counter

import numpy as np
import cv2

# -------------------------------------------------------------------
# Allow imports from src/...
# -------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- Unicode-safe image IO (works with Cyrillic) ----------
def load_rgb_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img  # BGR is fine for shape


# ---------- Config ----------
CLASS_MAP = {
    "signature": 0,
    "stamp": 1,
    "qr": 2,
}


def build_yolo_dataset_raw(
    annotations_json: str = "outputs/selected_annotations.json",
    raw_images_dir: str = "data/pngs_processed",
    out_dir: str = "data/yolo_raw",
    train_ratio: float = 0.85,
    seed: int = 42,
):
    """
    Build YOLO dataset directly from raw PDF→PNG pages.
    Uses page_size from JSON to scale bboxes to PNG coordinates.
    Performs stratified train/val split by class presence.
    """

    random.seed(seed)

    # --- Load annotations ---
    with open(annotations_json, "r", encoding="utf-8") as f:
        annotations = json.load(f)

    raw_images_dir = Path(raw_images_dir)
    out_dir = Path(out_dir)

    images_train = out_dir / "images" / "train"
    images_val = out_dir / "images" / "val"
    labels_train = out_dir / "labels" / "train"
    labels_val = out_dir / "labels" / "val"

    for d in [images_train, images_val, labels_train, labels_val]:
        d.mkdir(parents=True, exist_ok=True)

    # --- Build records: one per PNG page ---
    records = []
    for img_path in sorted(raw_images_dir.glob("*.png")):
        filename = img_path.name          # e.g. "АПЗ-2_page_001.png"
        stem = img_path.stem

        # Parse "<pdfname>_page_<num>"
        try:
            pdf_name, page_str = stem.rsplit("_page_", 1)
            page_idx = int(page_str)
            page_key = f"page_{page_idx}"         # "page_1"
            pdf_key = pdf_name + ".pdf"           # "АПЗ-2.pdf"
        except ValueError:
            print(f"[WARN] Cannot parse pdf/page from {filename}")
            continue

        if pdf_key not in annotations or page_key not in annotations[pdf_key]:
            # no annotations for this page
            page_ann = []
            page_size = None
        else:
            page_data = annotations[pdf_key][page_key]
            page_ann = page_data.get("annotations", [])
            page_size = page_data.get("page_size", None)

        # load image to know its size
        try:
            img_bgr = load_rgb_unicode(img_path)
        except FileNotFoundError as e:
            print("[ERROR]", e)
            continue

        h_img, w_img = img_bgr.shape[:2]

        if page_size is not None:
            pw = float(page_size["width"])
            ph = float(page_size["height"])
            sx = w_img / pw
            sy = h_img / ph
        else:
            sx = sy = 1.0

        # compute which classes are present on this page
        classes_on_page = set()
        for item in page_ann:
            ann_id, entry = next(iter(item.items()))
            cls = entry["category"]
            if cls in CLASS_MAP:
                classes_on_page.add(cls)

        records.append(
            {
                "img_path": img_path,
                "filename": filename,
                "stem": stem,
                "pdf_key": pdf_key,
                "page_key": page_key,
                "annotations": page_ann,
                "page_size": page_size,
                "sx": sx,
                "sy": sy,
                "w_img": w_img,
                "h_img": h_img,
                "classes": classes_on_page,
            }
        )

    if not records:
        print("[YOLO_RAW] No records found, aborting.")
        return

    # --- Stratified split by class presence ---
    N = len(records)
    target_val_images = max(1, int(N * (1 - train_ratio)))

    img_class_counts = Counter()
    for rec in records:
        for c in rec["classes"]:
            img_class_counts[c] += 1

    print("[STRAT-RAW] Image-level class counts:", img_class_counts)

    target_val_per_class = {}
    for c, count in img_class_counts.items():
        if count == 0:
            continue
        target = int(round(target_val_images * (count / N)))
        target_val_per_class[c] = max(1, target)

    print("[STRAT-RAW] Target val images per class:", target_val_per_class)

    random.shuffle(records)
    val_indices = set()
    val_class_counts = Counter()

    for i, rec in enumerate(records):
        if len(val_indices) >= target_val_images:
            break
        if not rec["classes"]:
            continue

        needs_any = False
        for c in rec["classes"]:
            if c in target_val_per_class and val_class_counts[c] < target_val_per_class[c]:
                needs_any = True
                break
        if needs_any:
            val_indices.add(i)
            for c in rec["classes"]:
                val_class_counts[c] += 1

    # fill remaining val slots randomly
    for i, rec in enumerate(records):
        if len(val_indices) >= target_val_images:
            break
        if i in val_indices:
            continue
        val_indices.add(i)

    print("[STRAT-RAW] Final val size:", len(val_indices))
    print("[STRAT-RAW] Class counts in val:", val_class_counts)

    # --- Write images + labels in YOLO format ---
    for i, rec in enumerate(records):
        img_path = rec["img_path"]
        filename = rec["filename"]
        stem = rec["stem"]
        annotations_page = rec["annotations"]
        sx = rec["sx"]
        sy = rec["sy"]
        w_img = rec["w_img"]
        h_img = rec["h_img"]

        is_val = i in val_indices

        if is_val:
            img_dst = images_val / filename
            lbl_dst = labels_val / f"{stem}.txt"
        else:
            img_dst = images_train / filename
            lbl_dst = labels_train / f"{stem}.txt"

        shutil.copy2(img_path, img_dst)

        # build label file
        with lbl_dst.open("w", encoding="utf-8") as f_lbl:
            for item in annotations_page:
                ann_id, entry = next(iter(item.items()))
                cls = entry["category"]
                if cls not in CLASS_MAP:
                    continue
                cid = CLASS_MAP[cls]

                bbox = entry["bbox"]
                x, y = bbox["x"], bbox["y"]
                w, h = bbox["width"], bbox["height"]

                # scale from PDF/page → PNG
                x_png = x * sx
                y_png = y * sy
                w_png = w * sx
                h_png = h * sy

                # YOLO normalized
                xc = (x_png + w_png / 2) / w_img
                yc = (y_png + h_png / 2) / h_img
                wn = w_png / w_img
                hn = h_png / h_img

                f_lbl.write(f"{cid} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}\n")

    print(f"[YOLO_RAW] Dataset created at: {out_dir}")


if __name__ == "__main__":
    print("[YOLO_RAW] Building dataset from raw PNGs...")
    build_yolo_dataset_raw()
    print("[YOLO_RAW] Done.")
