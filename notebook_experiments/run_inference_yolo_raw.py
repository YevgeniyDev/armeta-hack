import os
from pathlib import Path

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = PROJECT_ROOT / "models" / "best_yolo_raw.pt"
INPUT_DIR = PROJECT_ROOT / "data" / "pngs_processed_testing"
OUT_DIR = PROJECT_ROOT / "outputs" / "predictions_yolo_raw_testing"

def main():
    print(f"[INF] Loading model from: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run prediction on whole folder
    # Ultralytics will save visualized images with boxes
    results = model.predict(
        source=str(INPUT_DIR),
        imgsz=1024,
        conf=0.25,
        save=True,
        project=str(OUT_DIR),   # where to put runs
        name="val_preds",
        exist_ok=True
    )

    print(f"[INF] Done. Predictions are in: {OUT_DIR / 'val_preds'}")


if __name__ == "__main__":
    main()
