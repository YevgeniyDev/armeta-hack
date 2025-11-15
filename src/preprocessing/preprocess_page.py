# src/preprocessing/preprocess_page.py

from pathlib import Path
import json
from tqdm import tqdm

from .resize_pad import load_rgb, resize_and_pad, save_rgb


def preprocess_all_pages(
    src_dir: str = "data/pngs_processed",
    dst_dir: str = "data/preprocessed",
    target_size: int = 1024,
    split: str = "train"
):
    """
    Preprocess all page images in src_dir:
      - load
      - resize + pad
      - save to dst_dir/<split>/
      - save metadata (scale, pad_left, pad_top) in data/metadata/

    Args:
        src_dir: directory with raw page images
        dst_dir: base directory for preprocessed pages
        target_size: output image size (square)
        split: "train", "val", or "test"
    """
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir) / split
    meta_dir = Path("data/metadata")
    meta_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(src_dir.glob("*.png"))  # change if jpg

    metadata = {}

    for img_path in tqdm(image_paths, desc=f"Preprocessing ({split})"):
        img = load_rgb(img_path)
        resized_padded, scale, pad_left, pad_top = resize_and_pad(
            img, target_size=target_size
        )

        out_name = img_path.name  # keep same filename
        out_path = dst_dir / out_name
        save_rgb(out_path, resized_padded)

        metadata[out_name] = {
            "scale": scale,
            "pad_left": pad_left,
            "pad_top": pad_top,
            "orig_width": img.shape[1],
            "orig_height": img.shape[0],
            "target_size": target_size,
        }

    # Save metadata as JSON
    meta_path = meta_dir / f"preprocess_meta_{split}.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Saved metadata to {meta_path}")


if __name__ == "__main__":
    # For hackathon: at first you may treat everything as train, then later split.
    preprocess_all_pages(split="train")
