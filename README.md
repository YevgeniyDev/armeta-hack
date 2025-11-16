# Armeta Inspector – AI-Powered Document Analysis & PDF Reporting Platform

Armeta Inspector is a full-stack system for detecting **signatures**, **stamps**, and **QR codes** in PDF documents and images.  
It includes:

- 🚀 FastAPI backend (YOLO-based detection + PDF reporting)
- 🖥️ React + Tailwind frontend (interactive viewer)
- 🧩 Batch processing CLI script
- 📄 Beautiful dark-themed PDF summary generator
- 📦 Runtime storage of document pages
- 🔍 Zooming, panning, bounding boxes, filters

---

## 📁 Project Structure

```bash
armeta-hack/
│
├── armeta_backend/
│ ├── main.py # FastAPI server + YOLO detection + PDF reporting
│ ├── report_pdf.py # just a testing file to create pdf report(unnecessary now, but in case anything it's still here)
│
├── armeta-frontend/
│ ├── src/
│ │ ├── App.tsx # Main React SPA
│ │ ├── api.ts # Backend API integration
| | ├── types.ts # Detection classes
│ │ ├── main.tsx # Displaying
│ │ ├── assets/
│ │ │ └── favicon.png # logo
│ │ ├── components/
│ │ │ └── PageViewer.tsx # Zoom + Pan viewer
| └── public/
│
├── data/
│ ├── metadata/ # Preprocessing data about resizing/padding
│ ├── pdfs_given/ # PDF files that were given for training and testing
│ ├── pngs_kaggle/ # PNGs from open-source databases
| ├── pngs_processed/ # Converted PNGs from PDFs for training
| ├── pngs_processed_testing/ # Converted PNGs from PDFs for testing
| ├── preprocessed/ # tiles(PNGs divided into tiles) for training and testing
| ├── testing/ # PDFs for testing
| ├── yolo_raw/ # Data ready for training(PNGs with labels)
|
├── models/ # trained models, ready for testing
|
├── notebook_experiments/ # Experimental codes to run inference, resizing and visualization of annotations
|
├── outputs/ # Resulting PNGs from finished models with labelled boxes + json results and json for training
|
├── src/ # main codes used for preprocessing and JSON output
│ ├── batch_detect_to_json.py # CLI tool for bulk image detection
| ├── preprocessing # building of datasets, pdf2image converter, resizing, bbox utils
| └── tiling # Tiling codes
│
└── requirements.txt # Requirements (dependencies)
|
└── selected_annotations_generated.json # resulting JSON file
|
└── README.md
```
---

## ⚙️ Backend Installation (FastAPI + YOLO)

### 1. Create & activate virtual environment
```bash
cd armeta_backend
python -m venv venv
venv\Scripts\activate # Windows
source venv/bin/activate # macOS/Linux
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```
### 3. Run backend
```bash
uvicorn armeta_backend.main:app --reload # run the backend
```
Backend runs at:
API root → http://127.0.0.1:8000
Swagger docs → http://127.0.0.1:8000/docs

## 🎨 Frontend Installation (React + Tailwind)
### 1. Install dependencies
```bash
cd armeta-frontend
npm install
```

### 2. Run development server
```bash
npm run dev
```

Frontend runs at:
➡️ http://127.0.0.1:5173

## 🔥 Key Features
### Backend
```bash
✔ Accepts PDFs & images
✔ Converts PDF → PNG pages
✔ Runs YOLO detection on each page
✔ Saves results to runtime_data/<doc_id>/result.json
✔ Builds a dark-themed PDF report:
    Logo header
    File metadata
    Total detections with badges
    Per-page breakdown
    Average confidence score
    Summary page merged with original PDF
```

### Frontend
```bash
✔ Drag-and-drop upload
✔ Loading spinner
✔ Multi-page preview
✔ Zoom (wheel), pan (drag)
✔ Bounding boxes (signature, stamp, QR)
✔ Filters by class
✔ Confidence slider
✔ Download report button
```

## 📄 Dark PDF Report Example

### Generated report includes:
```bash
  Logo + title header
  File name (supports Cyrillic)
  Pages analyzed
  Average confidence score
  Detection totals
  Per-page summary (table)
  Dark background matching site branding
```

## 🧩 Batch Processing Tool (CLI)
### Use when analyzing a whole folder:
```bash
python -m src.batch_detect_to_json
```
It saves the resulting JSON file into outputs/ as a "selected_annotations_generated.json"

## 📦 Runtime Storage Layout
### After each POST /analyze, backend creates:
```bash
backend/runtime_data/<doc_id>/
│
├── source.pdf # Original uploaded file
├── pages/ # Extracted PNG pages
│   ├── page_001.png
│   ├── page_002.png
│   └── ...
└── result.json # Final detections (DocResult)
```

## 🧪 How to Test the System
```bash
Start backend + frontend
Drag-and-drop any PDF or image
Wait for the loader
View detections, zoom/pan, filter
Click Download report
Open final <file>_report.pdf
```

## 🛠 Technologies Used
### Backend:
```bash
FastAPI
YOLOv8 (Ultralytics)
OpenCV
Numpy
PyMuPDF
ReportLab
PyPDF
```

### Frontend:
```bash
React + TypeScript
TailwindCSS
Vite
```

## 🚀 Deployment
### Backend
```bash
uvicorn armeta_backend.main:app --reload # run the backend
```

### Frontend
```bash
npm run build
```

## 📞 Support
### If you'd like:
```bash
  OCR text extraction
  Auto-translation
  Document validation
  More visualizations
  Signature forgery detection
```
### Feel free to ask!
