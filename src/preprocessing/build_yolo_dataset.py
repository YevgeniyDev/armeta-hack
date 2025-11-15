import json
import shutil
from pathlib import Path
from src.preprocessing.bbox_utils import convert_orig_to_preprocessed, xywh_to_yolo, clip_bbox

# Map your categories → YOLO class IDs
CLASS_MAP = {
    "signature": 0,
    "stamp": 1,
    "qr": 2,
    "qr_code": 2,
}


def build_yolo_dataset(
    annotations_json="outputs/selected_annotations.json",
    metadata_json="data/metadata/preprocess_meta_train.json",
    preproc_dir="data/preprocessed/train",
    out_dir="data/yolo",
    train_ratio=0.85
):
    # Load annotation json
    with open(annotations_json, "r", encoding="utf-8") as f:
        annotations = json.load(f)

    # Load metadata json
    with open(metadata_json, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    preproc_dir = Path(preproc_dir)
    out_dir = Path(out_dir)

    # Output directories
    img_train = out_dir / "images" / "train"
    img_val   = out_dir / "images" / "val"
    lbl_train = out_dir / "labels" / "train"
    lbl_val   = out_dir / "labels" / "val"

    for d in [img_train, img_val, lbl_train, lbl_val]:
        d.mkdir(parents=True, exist_ok=True)

    preproc_images = sorted(preproc_dir.glob("*.png"))
    n_train = int(len(preproc_images) * train_ratio)

    for idx, img_path in enumerate(preproc_images):

        filename = img_path.name     # "АПЗ-2_page_001.png"
        stem = img_path.stem         # "АПЗ-2_page_001"

        # Determine PDF name + page number
        try:
            pdf_name, page_str = stem.rsplit("_page_", 1)
            page_key = "page_" + str(int(page_str))   # "page_1"
        except:
            print("[WARN] Could not parse page number:", filename)
            continue

        pdf_key = pdf_name + ".pdf"
        if pdf_key not in annotations:
            continue
        if page_key not in annotations[pdf_key]:
            continue

        page_annots = annotations[pdf_key][page_key]["annotations"]

        # metadata for this preprocessed image
        if filename not in metadata:
            print("[WARN] No metadata:", filename)
            continue
        meta = metadata[filename]

        # train or val?
        if idx < n_train:
            img_dst = img_train / filename
            lbl_dst = lbl_train / (stem + ".txt")
        else:
            img_dst = img_val / filename
            lbl_dst = lbl_val / (stem + ".txt")

        # copy image
        shutil.copy2(img_path, img_dst)

        # write YOLO label
        with open(lbl_dst, "w", encoding="utf-8") as f_lbl:

            for ann_item in page_annots:
                # ann_item = {"annotation_XX": {...}}
                entry = next(iter(ann_item.values()))

                cls = entry["category"]
                bbox = entry["bbox"]

                cid = CLASS_MAP[cls]

                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]

                # Transform original→preprocessed coords
                x_p, y_p, w_p, h_p = convert_orig_to_preprocessed(x, y, w, h, meta)
                x_p, y_p, w_p, h_p = clip_bbox(x_p, y_p, w_p, h_p)

                # YOLO normalized
                xc, yc, wn, hn = xywh_to_yolo(x_p, y_p, w_p, h_p)

                f_lbl.write(f"{cid} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}\n")

    print(f"[YOLO] Dataset created at: {out_dir}")


if __name__ == "__main__":
    print("[YOLO] Starting dataset build...")
    build_yolo_dataset(
        annotations_json="outputs/selected_annotations.json",
        metadata_json="data/metadata/preprocess_meta_train.json",
        preproc_dir="data/preprocessed/train",
        out_dir="data/yolo",
        train_ratio=0.85,
    )
    print("[YOLO] Done.")

