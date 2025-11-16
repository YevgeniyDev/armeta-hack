# batch_detect_to_json.py

import json
from pathlib import Path
from typing import Dict, List

import fitz                        # PyMuPDF
from PIL import Image
from ultralytics import YOLO


# --- настройки ----------------------------------------------------

# Путь к обученной модели
MODEL_PATH = Path("models/best_yolo_raw.pt")

# Какие классы соответствуют id модели (как в backend-е)
ID2LABEL = {
    0: "signature",
    1: "stamp",
    2: "qr",
}

# DPI для конвертации PDF в картинки
PDF_DPI = 200

# Порог уверенности
CONF_THRESH = 0.25


# --- вспомогательные функции --------------------------------------


def run_yolo_on_image(model: YOLO, img_path: Path) -> List[Dict]:

    results = model.predict(
        source=str(img_path),
        imgsz=1024,
        conf=CONF_THRESH,
        verbose=False,
    )

    if not results:
        return []

    r = results[0]
    boxes = r.boxes
    if boxes is None:
        return []

    annotations = []
    for i, (xyxy, cls) in enumerate(zip(boxes.xyxy, boxes.cls), start=1):
        x1, y1, x2, y2 = [float(v) for v in xyxy.tolist()]
        w = x2 - x1
        h = y2 - y1
        area = w * h

        cid = int(cls.item())
        category = ID2LABEL.get(cid, "unknown")

        annotations.append(
            {
                f"annotation_{i}": {
                    "category": category,
                    "bbox": {
                        "x": x1,
                        "y": y1,
                        "width": w,
                        "height": h,
                    },
                    "area": area,
                }
            }
        )

    return annotations


def process_pdf(model: YOLO, pdf_path: Path, tmp_dir: Path) -> Dict:
    """
    Обрабатывает один PDF: возвращает dict вида
    {
      "page_1": {
        "annotations": [...],
        "page_size": {"width": ..., "height": ...}
      },
      ...
    }
    """
    doc = fitz.open(pdf_path)
    pages_dict: Dict[str, Dict] = {}

    zoom = PDF_DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for page_index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        width, height = pix.width, pix.height

        # сохраняем временную картинку для YOLO
        img_path = tmp_dir / f"{pdf_path.stem}_page_{page_index}.png"
        pix.save(str(img_path))

        anns = run_yolo_on_image(model, img_path)

        page_key = f"page_{page_index}"
        pages_dict[page_key] = {
            "annotations": anns,
            "page_size": {"width": width, "height": height},
        }

    doc.close()
    return pages_dict


def process_image(model: YOLO, img_path: Path) -> Dict:
    """
    Обрабатывает одиночную картинку как документ из одной страницы.
    Возвращает:
    {
      "page_1": {
        "annotations": [...],
        "page_size": {"width": ..., "height": ...}
      }
    }
    """
    with Image.open(img_path) as im:
        width, height = im.size

    anns = run_yolo_on_image(model, img_path)

    return {
        "page_1": {
            "annotations": anns,
            "page_size": {"width": width, "height": height},
        }
    }


def build_annotations_for_folder(
    input_dir: Path,
    output_json: Path,
) -> None:
    """
    Обходит все PDF и изображения в папке input_dir,
    формирует JSON наподобие selected_annotations.json и сохраняет его.
    """
    model = YOLO(str(MODEL_PATH))

    input_dir = input_dir.resolve()
    tmp_dir = input_dir / "_tmp_pages"
    tmp_dir.mkdir(exist_ok=True)

    result: Dict[str, Dict] = {}

    pdf_exts = {".pdf"}
    img_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        # PDF
        if suffix in pdf_exts:
            print(f"Processing PDF: {path.name}")
            result[path.name] = process_pdf(model, path, tmp_dir)

        # Картинки
        elif suffix in img_exts:
            print(f"Processing image: {path.name}")
            result[path.name] = process_image(model, path)

    # сохраняем JSON
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved annotations to: {output_json}")


# --- точка входа --------------------------------------------------

if __name__ == "__main__":
    # Папка с PDF/картинками
    input_folder = Path("data/pdfs_given")
    # Куда сохранить аннотации
    output_path = Path("outputs/selected_annotations_generated.json")

    build_annotations_for_folder(input_folder, output_path)
