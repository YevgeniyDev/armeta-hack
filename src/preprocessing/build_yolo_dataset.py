import json
import shutil
import random
from pathlib import Path
from collections import Counter

from src.preprocessing.bbox_utils import (
    convert_orig_to_preprocessed,
    xywh_to_yolo,
    clip_bbox,
)

# Map your categories → YOLO class IDs
CLASS_MAP = {
    "signature": 0,
    "stamp": 1,
    "qr": 2,
}


def build_yolo_dataset(
    annotations_json="outputs/selected_annotations.json",
    metadata_json="data/metadata/preprocess_meta_train.json",
    preproc_dir="data/preprocessed/train",
    out_dir="data/yolo",
    train_ratio=0.85,
    seed: int = 42,
):
    """
    Build YOLO dataset with STRATIFIED train/val split by class presence.
    Each image can have multiple classes; we try to preserve class
    distribution and make sure each class is present in val if possible.
    """

    random.seed(seed)

    # --- Load JSONs ---
    with open(annotations_json, "r", encoding="utf-8") as f:
        annotations = json.load(f)

    with open(metadata_json, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    preproc_dir = Path(preproc_dir)
    out_dir = Path(out_dir)

    # --- Prepare output dirs ---
    img_train = out_dir / "images" / "train"
    img_val = out_dir / "images" / "val"
    lbl_train = out_dir / "labels" / "train"
    lbl_val = out_dir / "labels" / "val"

    for d in [img_train, img_val, lbl_train, lbl_val]:
        d.mkdir(parents=True, exist_ok=True)

    preproc_images = sorted(preproc_dir.glob("*.png"))

    # --- Build per-image records with class presence info ---
    records = []  # one entry per image with classes on that page

    for img_path in preproc_images:
        filename = img_path.name       # "АПЗ-2_page_001.png"
        stem = img_path.stem           # "АПЗ-2_page_001"

        # parse "<pdfname>_page_<num>"
        try:
            pdf_name, page_str = stem.rsplit("_page_", 1)
            page_key = "page_" + str(int(page_str))   # "page_1"
        except ValueError:
            print("[WARN] Cannot parse page index from", filename)
            continue

        pdf_key = pdf_name + ".pdf"

        if pdf_key not in annotations:
            # no annotations for this pdf at all
            page_annots = []
        else:
            pages = annotations[pdf_key]
            if page_key not in pages:
                page_annots = []
            else:
                page_annots = pages[page_key]["annotations"]

        if filename not in metadata:
            print("[WARN] No metadata for", filename)
            continue
        meta = metadata[filename]

        # collect set of classes present on this page
        classes_on_page = set()
        for ann_item in page_annots:
            entry = next(iter(ann_item.values()))
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
                "meta": meta,
                "annotations": page_annots,
                "classes": classes_on_page,
            }
        )

    if not records:
        print("[YOLO] No valid records found, aborting.")
        return

    # --- Compute stratified split targets ---
    N = len(records)
    target_val_images = max(1, int(N * (1 - train_ratio)))

    # count how many images contain each class at least once
    img_class_counts = Counter()
    for rec in records:
        for c in rec["classes"]:
            img_class_counts[c] += 1

    print("[STRAT] Image-level class counts:", img_class_counts)

    # for each class, how many val images we want
    target_val_per_class = {}
    for c, count in img_class_counts.items():
        if count == 0:
            continue
        # proportionally scale, but at least 1 if possible
        target = int(round(target_val_images * (count / N)))
        target_val_per_class[c] = max(1, target)

    print("[STRAT] Target val images per class:", target_val_per_class)

    # --- Stratified assignment of images to val ---
    random.shuffle(records)

    val_indices = set()
    val_class_counts = Counter()

    for i, rec in enumerate(records):
        if len(val_indices) >= target_val_images:
            break

        # if this image has no classes, skip for now (can be added later)
        if not rec["classes"]:
            continue

        # check if adding this image helps fill some class target
        needs_any_class = False
        for c in rec["classes"]:
            if c in target_val_per_class and val_class_counts[c] < target_val_per_class[c]:
                needs_any_class = True
                break

        if needs_any_class:
            val_indices.add(i)
            for c in rec["classes"]:
                val_class_counts[c] += 1

    # if val still too small, fill with remaining images (even if empty)
    for i, rec in enumerate(records):
        if len(val_indices) >= target_val_images:
            break
        if i in val_indices:
            continue
        val_indices.add(i)

    print("[STRAT] Final val size:", len(val_indices))
    print("[STRAT] Class counts in val:", val_class_counts)

    # --- Now actually write images + labels using this split ---
    for i, rec in enumerate(records):
        img_path = rec["img_path"]
        filename = rec["filename"]
        stem = rec["stem"]
        page_annots = rec["annotations"]
        meta = rec["meta"]

        # decide split
        is_val = i in val_indices

        if is_val:
            img_dst = img_val / filename
            lbl_dst = lbl_val / (stem + ".txt")
        else:
            img_dst = img_train / filename
            lbl_dst = lbl_train / (stem + ".txt")

        shutil.copy2(img_path, img_dst)

        # write label file
        with open(lbl_dst, "w", encoding="utf-8") as f_lbl:
            for ann_item in page_annots:
                entry = next(iter(ann_item.values()))
                cls = entry["category"]

                if cls not in CLASS_MAP:
                    print(f"[WARN] Unknown category '{cls}', skipping.")
                    continue

                cid = CLASS_MAP[cls]
                bbox = entry["bbox"]
                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]

                # original PDF → preprocessed coords
                x_p, y_p, w_p, h_p = convert_orig_to_preprocessed(x, y, w, h, meta)
                x_p, y_p, w_p, h_p = clip_bbox(x_p, y_p, w_p, h_p)

                # → YOLO normalized
                xc, yc, wn, hn = xywh_to_yolo(x_p, y_p, w_p, h_p)

                f_lbl.write(f"{cid} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}\n")

    print(f"[YOLO] Dataset created at: {out_dir}")


if __name__ == "__main__":
    print("[YOLO] Starting stratified dataset build...")
    build_yolo_dataset()
    print("[YOLO] Done.")
