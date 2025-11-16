# backend/main.py

import uuid
import json
from pathlib import Path
from typing import List, Literal

import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ultralytics import YOLO

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from pypdf import PdfReader, PdfWriter

# -------------------------------------------------------
# Конфиг путей
# -------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime_data"  # сюда сохраняем страницы
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
BACKEND_BASE = "http://127.0.0.1:8000"

MODEL_PATH = PROJECT_ROOT / "models" / "best_yolo_raw.pt"

LOGO_PATH = PROJECT_ROOT / "assets" / "favicon.png"
STATIC_URL = "/static"  # URL-префикс для картинок

FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
pdfmetrics.registerFont(TTFont("Roboto", str(FONT_DIR / "Roboto-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Roboto-Bold", str(FONT_DIR / "Roboto-Bold.ttf")))

# -------------------------------------------------------
# Классы (должны совпадать с обучением: 0=signature,1=stamp,2=qr)
# -------------------------------------------------------
ID2LABEL = {
    0: "signature",
    1: "stamp",
    2: "qr",
}
LABEL_TYPE = Literal["signature", "stamp", "qr"]


# -------------------------------------------------------
# Pydantic-схемы (под твой фронт)
# -------------------------------------------------------
class Detection(BaseModel):
    id: str
    label: LABEL_TYPE
    score: float
    # нормализованные [0,1] координаты top-left + размер
    x: float
    y: float
    w: float
    h: float


class PageResult(BaseModel):
    pageIndex: int
    imageUrl: str
    detections: List[Detection]


class DocResult(BaseModel):
    id: str
    filename: str
    pages: List[PageResult]


# -------------------------------------------------------
# Инициализация FastAPI + CORS
# -------------------------------------------------------
app = FastAPI(title="Armeta Document Inspector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Отдаём картинки как статику
app.mount(
    STATIC_URL,
    StaticFiles(directory=RUNTIME_DIR),
    name="static",
)

# Загружаем модель один раз при старте процесса
print(f"[API] Loading YOLO model from: {MODEL_PATH}")
model = YOLO(str(MODEL_PATH))
print("[API] Model loaded")


# -------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------
def save_upload_to_temp(upload: UploadFile, dest: Path) -> None:
    """Сохранить UploadFile на диск."""
    data = upload.file.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int = 300) -> List[Path]:
    """Конвертировать PDF в PNG-страницы (без кириллицы в именах)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    page_paths: List[Path] = []

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_name = f"page_{i + 1:03d}.png"
        img_path = out_dir / img_name
        pix.save(img_path.as_posix())
        page_paths.append(img_path)

    doc.close()
    return page_paths


def image_from_upload(upload: UploadFile, out_path: Path) -> Path:
    """Сохранить одиночное изображение (png/jpg) в runtime."""
    data = upload.file.read()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return out_path


def run_yolo_on_image(img_path: Path, conf: float = 0.25) -> List[Detection]:
    """Запустить YOLO на одной картинке и вернуть список Detection."""
    results = model.predict(
        source=str(img_path),
        imgsz=1024,
        conf=conf,
        verbose=False,
    )

    detections: List[Detection] = []

    if not results:
        return detections

    r = results[0]
    h_img, w_img = r.orig_shape  # (H, W)

    boxes = r.boxes
    if boxes is None:
        return detections

    for i, (xyxy, cls, score) in enumerate(
        zip(boxes.xyxy, boxes.cls, boxes.conf)
    ):
        x1, y1, x2, y2 = xyxy.tolist()
        cid = int(cls.item())
        conf_score = float(score.item())

        if cid not in ID2LABEL:
            continue

        label: LABEL_TYPE = ID2LABEL[cid]  # type: ignore

        # приводим к top-left + width/height в пикселях
        w_box = x2 - x1
        h_box = y2 - y1

        # нормализуем [0,1] относительно размеров изображения
        x_norm = max(0.0, min(1.0, x1 / w_img))
        y_norm = max(0.0, min(1.0, y1 / h_img))
        w_norm = max(0.0, min(1.0, w_box / w_img))
        h_norm = max(0.0, min(1.0, h_box / h_img))

        detections.append(
            Detection(
                id=f"det_{i}",
                label=label,
                score=conf_score,
                x=x_norm,
                y=y_norm,
                w=w_norm,
                h=h_norm,
            )
        )

    return detections


# -------------------------------------------------------
# Эндпоинты анализа
# -------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=DocResult)
async def analyze_document(file: UploadFile = File(...)):
    """
    Принимает PDF или изображение.
    Возвращает DocResult в формате, который ожидает фронт.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    doc_id = str(uuid.uuid4())
    original_name = file.filename
    suffix = Path(original_name).suffix.lower()

    doc_dir = RUNTIME_DIR / doc_id
    pages_dir = doc_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    pages: List[Path] = []

    # 1) PDF → много страниц
    if suffix == ".pdf":
        tmp_pdf_path = doc_dir / "source.pdf"
        save_upload_to_temp(file, tmp_pdf_path)
        pages = pdf_to_images(tmp_pdf_path, pages_dir, dpi=300)

    # 2) Картинка → одна "страница"
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        img_path = pages_dir / "page_001.png"
        image_from_upload(file, img_path)
        pages = [img_path]

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Please upload PDF or image.",
        )

    # 3) Запускаем YOLO по каждой странице
    page_results: List[PageResult] = []

    for idx, page_path in enumerate(sorted(pages)):
        detections = run_yolo_on_image(page_path, conf=0.25)

        # URL для фронта: /static/<doc_id>/pages/page_001.png
        rel_path = page_path.relative_to(RUNTIME_DIR).as_posix()
        image_url = f"{BACKEND_BASE}{STATIC_URL}/{rel_path}"

        page_results.append(
            PageResult(
                pageIndex=idx,
                imageUrl=image_url,
                detections=detections,
            )
        )

    doc_result = DocResult(
        id=doc_id,
        filename=original_name,
        pages=page_results,
    )

    # Сохраняем результат для последующей генерации отчёта
    result_path = doc_dir / "result.json"
    result_path.write_text(
        doc_result.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return doc_result


# -------------------------------------------------------
# Генерация красивого summary-листа (тёмный стиль)
# -------------------------------------------------------
def build_summary_page(summary_path: Path, doc: DocResult, page_size) -> None:
    """
    Красивый dark-report под размер исходного PDF (A4, A3, ...).

    page_size: (width, height) в пунктах (1/72").
    """
    width, height = page_size
    c = canvas.Canvas(str(summary_path), pagesize=page_size)

    # ---------- Цвета в стиле фронта ----------
    bg_page = HexColor("#020617")      # общий фон (почти чёрный)
    bg_header = HexColor("#020617")    # шапка
    bg_card = HexColor("#020617")      # карточка totals
    bg_chip = {
        "signature": HexColor("#10b981"),  # emerald-500
        "stamp": HexColor("#0ea5e9"),      # sky-500
        "qr": HexColor("#d946ef"),         # fuchsia-500
    }
    fg_primary = HexColor("#e5e7eb")   # text-slate-200
    fg_muted = HexColor("#9ca3af")     # text-slate-400
    accent = HexColor("#22c55e")       # зелёный
    grid_color = HexColor("#334155")   # линии таблицы

    # ---------- Фон страницы ----------
    c.setFillColor(bg_page)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    margin_x = width * 0.07

    # ---------- Хедер с логотипом ----------
    header_h = height * 0.14
    c.setFillColor(bg_header)
    c.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    # базовый размер для логотипа
    logo_side = header_h * 0.6
    logo_x = margin_x
    logo_y = height - header_h + (header_h - logo_side) / 2

    if LOGO_PATH.exists():
        # используем PNG-логотип
        logo_size = header_h * 0.7
        logo_side = logo_size  # чтобы дальше отталкиваться от реального размера
        logo_x = width * 0.045
        logo_y = height - header_h * 0.5 - logo_size / 2
        c.drawImage(
            str(LOGO_PATH),
            logo_x,
            logo_y,
            width=logo_size,
            height=logo_size,
            preserveAspectRatio=True,
            mask="auto",
        )
    else:
        # fallback: зелёный круг с буквой A
        logo_r = header_h * 0.28
        logo_cx = width * 0.07
        logo_cy = height - header_h / 2
        c.setFillColor(accent)
        c.circle(logo_cx, logo_cy, logo_r, fill=1, stroke=0)
        c.setFillColor(bg_header)
        c.setFont("Roboto-Bold", logo_r * 0.9)
        c.drawCentredString(logo_cx, logo_cy - logo_r * 0.35, "A")

    # текст справа от логотипа
    title_x = logo_x + logo_side + width * 0.035
    base = min(width, height)
    title_size = base * 0.040
    subtitle_size = base * 0.018

    c.setFillColor(fg_primary)
    c.setFont("Roboto-Bold", title_size)
    c.drawString(title_x, height - header_h * 0.45, "Armeta Inspector")

    c.setFillColor(fg_muted)
    c.setFont("Roboto", subtitle_size)
    c.drawString(
        title_x,
        height - header_h * 0.75,
        "Signatures · Stamps · QR codes",
    )

    # ---------- Информация о документе ----------
    cursor_y = height - header_h - height * 0.05

    filename = Path(doc.filename).name

    info_font = base * 0.020
    line_gap = info_font * 1.6

    c.setFillColor(fg_primary)
    c.setFont("Roboto", info_font)
    c.drawString(margin_x, cursor_y, f"File: {filename}")
    cursor_y -= line_gap

    c.setFillColor(fg_primary)
    c.setFont("Roboto", info_font)
    c.drawString(margin_x, cursor_y, f"Pages analyzed: {len(doc.pages)}")
    cursor_y -= line_gap * 1.8

    # ---------- Карточка Total detections ----------
    card_w = width * 0.86
    card_h = height * 0.24  # чуть выше, чтобы влезла строка avg conf
    card_x = margin_x
    card_y = cursor_y - card_h

    c.setFillColor(bg_card)
    c.roundRect(card_x, card_y, card_w, card_h, 12, fill=1, stroke=0)

    inner_margin = card_w * 0.045
    text_x = card_x + inner_margin
    text_y = card_y + card_h - inner_margin

    total_by_class: dict[str, int] = {}
    all_scores: list[float] = []

    for p in doc.pages:
        for d in p.detections:
            total_by_class[d.label] = total_by_class.get(d.label, 0) + 1
            all_scores.append(d.score)

    avg_conf = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # Заголовок карточки
    c.setFillColor(fg_primary)
    c.setFont("Roboto-Bold", info_font * 1.1)
    c.drawString(text_x, text_y, "Total detections")
    text_y -= line_gap * 0.9

    # Средний confidence
    c.setFillColor(fg_muted)
    c.setFont("Roboto", info_font * 0.95)
    c.drawString(text_x, text_y, f"Average confidence: {avg_conf * 100:.1f}%")
    text_y -= line_gap * 1.2

    # Список по классам
    c.setFont("Roboto", info_font)
    c.setFillColor(fg_primary)

    if total_by_class:
        for cls in ["signature", "stamp", "qr"]:
            if cls not in total_by_class:
                continue
            count = total_by_class[cls]

            chip_h = info_font * 1.4
            chip_w = card_w * 0.16
            chip_r = chip_h * 0.5

            # цветной бейдж
            c.setFillColor(bg_chip[cls])
            c.roundRect(
                text_x,
                text_y - chip_h * 0.35,
                chip_w,
                chip_h,
                chip_r,
                fill=1,
                stroke=0,
            )

            c.setFillColor(bg_page)
            c.setFont("Roboto-Bold", info_font * 0.9)
            label = (
                "Signature"
                if cls == "signature"
                else "Stamp" if cls == "stamp" else "QR code"
            )
            c.drawString(
                text_x + chip_h * 0.45,
                text_y,
                label,
            )

            c.setFillColor(fg_primary)
            c.setFont("Roboto", info_font)
            c.drawString(
                text_x + chip_w + info_font * 0.7,
                text_y,
                f"× {count}",
            )

            text_y -= line_gap * 1.15
    else:
        c.setFillColor(fg_muted)
        c.setFont("Roboto", info_font)
        c.drawString(text_x, text_y, "No detections found.")

    cursor_y = card_y - line_gap * 1.8

    # ---------- Per-page summary (таблица) ----------
    c.setFillColor(fg_primary)
    c.setFont("Roboto-Bold", info_font * 1.1)
    c.drawString(margin_x, cursor_y, "Per-page summary")
    cursor_y -= line_gap * 1.3

    col1_x = margin_x
    col2_x = margin_x + width * 0.22
    table_w = card_w

    c.setFont("Roboto-Bold", info_font * 0.95)
    c.setFillColor(fg_muted)
    c.drawString(col1_x, cursor_y, "Page")
    c.drawString(col2_x, cursor_y, "Detections")
    cursor_y -= line_gap * 0.9

    c.setStrokeColor(grid_color)
    c.setLineWidth(0.6)
    c.line(col1_x, cursor_y, col1_x + table_w, cursor_y)
    cursor_y -= line_gap * 0.7

    c.setFont("Roboto", info_font)
    c.setFillColor(fg_primary)

    for p in doc.pages:
        if cursor_y < height * 0.08:
            break

        local: dict[str, int] = {}
        for d in p.detections:
            local[d.label] = local.get(d.label, 0) + 1

        left = f"Page {p.pageIndex + 1}"
        if local:
            parts = []
            for cls in ["signature", "stamp", "qr"]:
                if cls in local:
                    pretty = (
                        "signature"
                        if cls == "signature"
                        else "stamp" if cls == "stamp" else "qr"
                    )
                    parts.append(f"{pretty} ×{local[cls]}")
            right = ", ".join(parts)
        else:
            right = "—"

        c.drawString(col1_x, cursor_y, left)
        c.drawString(col2_x, cursor_y, right)
        cursor_y -= line_gap * 0.95

    c.showPage()
    c.save()


# -------------------------------------------------------
# Эндпоинт скачивания отчёта
# -------------------------------------------------------
@app.get("/docs/{doc_id}/report")
async def download_report(doc_id: str):
    """
    Собирает PDF-отчет:
    1) summary-страница (того же размера, что и оригинальный PDF)
    2) оригинальный PDF, который пользователь залил.
    """
    doc_dir = RUNTIME_DIR / doc_id
    result_json = doc_dir / "result.json"
    source_pdf = doc_dir / "source.pdf"  # pdf мы так называли в analyze_document

    if not result_json.exists():
        raise HTTPException(status_code=404, detail="Analysis result not found")
    if not source_pdf.exists():
        raise HTTPException(
            status_code=404,
            detail="Original PDF not found (reports only for PDF uploads).",
        )

    # читаем сохраненный DocResult
    doc_data = json.loads(result_json.read_text(encoding="utf-8"))
    doc_result = DocResult.model_validate(doc_data)

    # читаем оригинальный pdf, получаем размер первой страницы
    orig_reader = PdfReader(str(source_pdf))
    first_page = orig_reader.pages[0]
    media_box = first_page.mediabox
    page_width = float(media_box.width)
    page_height = float(media_box.height)
    page_size = (page_width, page_height)

    # временный summary.pdf
    summary_path = doc_dir / "summary.pdf"
    build_summary_page(summary_path, doc_result, page_size=page_size)

    # финальный отчет
    report_path = doc_dir / f"{doc_id}_report.pdf"

    writer = PdfWriter()

    # 1) summary
    summary_reader = PdfReader(str(summary_path))
    for page in summary_reader.pages:
        writer.add_page(page)

    # 2) оригинальный pdf
    for page in orig_reader.pages:
        writer.add_page(page)

    with report_path.open("wb") as f:
        writer.write(f)

    # удаляем временный summary
    summary_path.unlink(missing_ok=True)

    download_name = f"{Path(doc_result.filename).stem}_report.pdf"

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=download_name,
    )
