# src/preprocessing/pdf_to_images.py

import fitz
from pathlib import Path
from typing import List


def pdf_to_images(
    pdf_path: str,
    out_dir: str,
    dpi: int = 300,
    img_format: str = "png"
) -> List[Path]:
    """
    Convert a PDF into page images.

    Args:
        pdf_path: path to the PDF file.
        out_dir: directory where page images will be saved.
        dpi: resolution for rendering.
        img_format: image format ('png' or 'jpg').

    Returns:
        List of paths to the saved page images.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    page_paths = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img_name = f"{pdf_path.stem}_page_{page_index+1:03d}.{img_format}"
        img_path = out_dir / img_name
        pix.save(img_path.as_posix())

        page_paths.append(img_path)

    doc.close()
    return page_paths


def convert_all_pdfs(
    pdf_dir: str = "data/testing",
    out_dir: str = "data/pngs_processed_testing",
    dpi: int = 300,
    img_format: str = "png"
):
    """
    Convert all PDFs in pdf_dir to images.
    """
    pdf_dir = Path(pdf_dir)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    all_page_paths = []

    for pdf_file in pdf_files:
        print(f"[PDF2IMG] Processing {pdf_file.name}")
        page_paths = pdf_to_images(
            pdf_path=pdf_file,
            out_dir=out_dir,
            dpi=dpi,
            img_format=img_format
        )
        all_page_paths.extend(page_paths)

    print(f"[PDF2IMG] Done. Total pages: {len(all_page_paths)}")
    return all_page_paths


if __name__ == "__main__":
    convert_all_pdfs()
