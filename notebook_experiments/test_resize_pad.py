import cv2
from pathlib import Path
from src.preprocessing.resize_pad import load_rgb, resize_and_pad, save_rgb
import os

os.environ["PYTHONUTF8"] = "1"

def test_resize_pad_on_all():
    # Input and output directories
    src_dir = Path("data/pngs_processed")
    out_dir = Path("data/resize_pad")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect all PNG files
    imgs = sorted(src_dir.glob("*.png"))
    
    assert len(imgs) > 0, f"No .png files found in {src_dir}"

    print(f"[TEST] Found {len(imgs)} images in {src_dir}")

    for img_file in imgs:
        print(f"\n[TEST] --- Processing: {img_file.name} ---")

        # 1. Load
        img = load_rgb(img_file)
        print(f"[TEST] Original shape: {img.shape}")

        # 2. Resize + pad
        padded_img, scale, pad_left, pad_top = resize_and_pad(img, target_size=1024)

        print(f"[TEST] Processed shape: {padded_img.shape}")
        print(f"[TEST] Scale: {scale}")
        print(f"[TEST] pad_left: {pad_left}, pad_top: {pad_top}")

        # 3. Save output
        out_path = out_dir / img_file.name
        save_rgb(out_path, padded_img)
        print(f"[TEST] Saved processed file → {out_path}")

        # 4. Assertions
        assert padded_img.shape[0] == 1024, "Height is not 1024"
        assert padded_img.shape[1] == 1024, "Width is not 1024"
        assert scale > 0, "Scale must be > 0"
        assert pad_left >= 0 and pad_top >= 0, "Padding must be >= 0"

    print("\n[TEST] resize_pad.py passed for ALL images ✓")


if __name__ == "__main__":
    test_resize_pad_on_all()
