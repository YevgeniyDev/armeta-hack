# backend/pdf_report.py

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from unidecode import unidecode

# Подключаем шрифты Inter (файлы должны лежать рядом с этим модулем)
pdfmetrics.registerFont(TTFont("Inter", "Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Inter-Bold", "Inter-Bold.ttf"))

# Цвета
DARK_BG = colors.HexColor("#020617")      # почти чёрный фон
CARD_BG = colors.HexColor("#0f172a")      # карточки / таблицы
TEXT = colors.HexColor("#e5e7eb")         # основной текст
TEXT_MUTED = colors.HexColor("#9ca3af")   # второстепенный текст
GRID = colors.HexColor("#334155")         # линии таблицы

# Эти оставим строками для <font color="...">
EMERALD_HEX = "#10b981"
SKY_HEX = "#0ea5e9"
FUCHSIA_HEX = "#d946ef"


def safe_filename(name: str) -> str:
    """Убираем кириллицу для безопасного отображения в отчёте."""
    return unidecode(name)


def _draw_dark_background(canv, doc):
    """Фон для каждой страницы (полностью тёмный)."""
    canv.saveState()
    w, h = A4
    canv.setFillColor(DARK_BG)
    canv.rect(0, 0, w, h, fill=1, stroke=0)
    canv.restoreState()


def build_dark_report(doc, out_path: Path) -> None:
    """
    Строит тёмный PDF-репорт формата A4 по объекту doc (DocResult из API).
    out_path: куда сохранить PDF.
    """
    pdf = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleDark",
        parent=styles["Heading1"],
        fontName="Inter-Bold",
        fontSize=24,
        textColor=TEXT,
        alignment=0,  # left
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "SubtitleDark",
        parent=styles["Normal"],
        fontName="Inter",
        fontSize=10,
        textColor=TEXT_MUTED,
        spaceAfter=20,
    )

    text_style = ParagraphStyle(
        "NormalDark",
        parent=styles["Normal"],
        fontName="Inter",
        fontSize=11,
        textColor=TEXT,
        leading=15,
    )

    label_style = ParagraphStyle(
        "LabelDark",
        parent=styles["Normal"],
        fontName="Inter",
        fontSize=10,
        textColor=TEXT_MUTED,
        leading=13,
    )

    story = []

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------
    file_display = safe_filename(doc.filename)

    story.append(Paragraph("Armeta Inspector", title_style))
    story.append(
        Paragraph("Signatures · Stamps · QR codes", subtitle_style)
    )

    story.append(Paragraph(f"File: <b>{file_display}</b>", text_style))
    story.append(Paragraph(f"Document ID: {doc.id}", label_style))
    story.append(
        Paragraph(f"Pages analyzed: <b>{len(doc.pages)}</b>", text_style)
    )
    story.append(Spacer(1, 14))

    # --------------------------------------------------
    # TOTAL DETECTIONS CARD
    # --------------------------------------------------
    total_counts = {"signature": 0, "stamp": 0, "qr": 0}
    for p in doc.pages:
        for d in p.detections:
            total_counts[d.label] += 1

    card_data = [
        [
            Paragraph(
                "<b>Total detections</b>",
                ParagraphStyle(
                    "CardTitle",
                    parent=text_style,
                    fontName="Inter-Bold",
                    fontSize=13,
                ),
            )
        ],
        [
            Paragraph(
                f"<font color='{EMERALD_HEX}'>Signature</font> × {total_counts['signature']}<br/>"
                f"<font color='{SKY_HEX}'>Stamp</font> × {total_counts['stamp']}<br/>"
                f"<font color='{FUCHSIA_HEX}'>QR code</font> × {total_counts['qr']}",
                text_style,
            )
        ],
    ]

    card_table = Table(card_data, colWidths=[450])
    card_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, CARD_BG),
            ]
        )
    )

    story.append(card_table)
    story.append(Spacer(1, 18))

    # --------------------------------------------------
    # PER-PAGE SUMMARY TABLE
    # --------------------------------------------------
    story.append(
        Paragraph(
            "<b>Per-page summary</b>",
            ParagraphStyle(
                "SectionTitle",
                parent=text_style,
                fontName="Inter-Bold",
                fontSize=13,
                spaceAfter=6,
            ),
        )
    )

    table_data = [
        [
            Paragraph("<b>Page</b>", text_style),
            Paragraph("<b>Detections</b>", text_style),
        ]
    ]

    for p in doc.pages:
        labels = {}
        for d in p.detections:
            labels[d.label] = labels.get(d.label, 0) + 1

        if labels:
            # фиксируем порядок: signature, stamp, qr
            parts = []
            for key, pretty in [
                ("signature", "signature"),
                ("stamp", "stamp"),
                ("qr", "qr"),
            ]:
                if key in labels:
                    parts.append(f"{pretty} ×{labels[key]}")
            row_text = ", ".join(parts)
        else:
            row_text = "–"

        table_data.append(
            [
                Paragraph(str(p.pageIndex + 1), text_style),
                Paragraph(row_text, ParagraphStyle(
                    "RowText",
                    parent=text_style,
                    textColor=TEXT,   # делаем строки поярче
                )),
            ]
        )

    table = Table(table_data, colWidths=[60, 360])
    table.setStyle(
        TableStyle(
            [
                # заголовок таблицы
                ("BACKGROUND", (0, 0), (-1, 0), CARD_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), TEXT),
                ("FONTNAME", (0, 0), (-1, 0), "Inter-Bold"),

                # строки
                ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),

                # сетка
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),

                # отступы
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)

    pdf.build(
        story,
        onFirstPage=_draw_dark_background,
        onLaterPages=_draw_dark_background,
    )
