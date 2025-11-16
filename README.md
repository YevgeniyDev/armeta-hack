=====================================================================
                         ARMETA INSPECTOR
        AI-Powered System for Document Analysis & PDF Reporting
=====================================================================

Armeta Inspector is a full-stack application for detecting
SIGNATURES, STAMPS, and QR CODES in documents (PDF & images).
It includes:

 - FastAPI Backend
 - YOLOv8 Detection Model
 - React Frontend (Drag & Drop)
 - Interactive Document Viewer (zoom + pan)
 - Stylish PDF Summary Report (Dark Theme)
 - Batch Folder Processing Script
 - Support for Cyrillic filenames
 - Downloadable combined report (summary + original PDF)
 - Confidence filtering and statistics

This file describes HOW TO INSTALL, HOW IT WORKS, and HOW TO USE the
whole project.


=====================================================================
1. PROJECT STRUCTURE
=====================================================================

armeta-inspector/
│
├─ backend/
│   ├─ main.py                     ← FastAPI server
│   ├─ models/best_yolo_raw.pt     ← YOLO detection model
│   ├─ assets/
│   │     ├─ favicon.png           ← Logo used in PDF
│   │     └─ fonts/*.ttf           ← Roboto fonts
│   ├─ runtime_data/               ← Uploaded files + generated data
│   └─ requirements.txt
│
├─ frontend/
│   ├─ src/
│   │     ├─ App.tsx               ← Main React UI
│   │     ├─ PageViewer.tsx        ← Zoom, pan, boxes
│   │     └─ api.ts                ← Requests to backend
│   └─ public/
│
├─ tools/
│   └─ batch_detect_to_json.py     ← Batch folder → JSON processing
│
└─ README.txt (this file)


=====================================================================
2. BACKEND INSTALLATION (FASTAPI)
=====================================================================

1. Open terminal in /backend

2. Create virtual environment:
      python -m venv venv

3. Activate:
   - Windows: venv\Scripts\activate
   - Mac/Linux: source venv/bin/activate

4. Install dependencies:
      pip install -r requirements.txt

5. Start server:
      uvicorn main:app --reload --port 8000

Backend will run at:
      http://127.0.0.1:8000

FastAPI endpoints:
  POST /analyze           → Analyze document
  GET  /docs/<id>/report  → Download PDF report
  GET  /health            → Health check


=====================================================================
3. FRONTEND INSTALLATION (REACT + VITE)
=====================================================================

1. Open terminal in /frontend
2. Install packages:
      npm install
3. Start dev server:
      npm run dev

Frontend available at:
      http://127.0.0.1:5173


=====================================================================
4. HOW THE SYSTEM WORKS (FULL PIPELINE)
=====================================================================

-----------------------------
STEP 1 — User uploads a PDF or image
-----------------------------
Frontend sends:
      POST /analyze

Backend:
 - Saves file into runtime_data/<uuid>/
 - Converts PDF → pages (PNG)
 - Runs YOLO model on each page
 - Produces detection list:
        bounding boxes
        class names
        confidence
 - Saves result.json
 - Returns page images + detected objects

-----------------------------
STEP 2 — Frontend displays results
-----------------------------
UI shows:
 - Preview of pages
 - Bounding boxes
 - Filtering buttons
 - Confidence slider
 - Interactive zoom + pan
 - Page switching
 - Drag & Drop upload
 - Loading spinner during processing

-----------------------------
STEP 3 — User downloads PDF report
-----------------------------
Frontend requests:
      GET /docs/<uuid>/report

Backend:
 - Reads result.json
 - Reads original PDF
 - Builds summary page (dark PDF)
   including:
      • Logo
      • File name (Cyrillic supported)
      • Pages analyzed
      • Average confidence
      • Total detections
      • Per-page table
 - Appends original PDF pages
 - Returns final report.pdf


=====================================================================
5. PDF SUMMARY REPORT DETAILS
=====================================================================

The generated PDF includes:

 - Dark theme (matches frontend style)
 - Logo from /backend/assets/favicon.png
 - Title: "Armeta Inspector"
 - Subheader: "Signatures · Stamps · QR codes"
 - File name (supports Cyrillic)
 - Pages analyzed
 - Average confidence of all detections
 - Total detections grouped by class:
       Signature, Stamp, QR code
 - Per-page summary table
 - Original PDF pages appended

Report uses Roboto font to correctly display Cyrillic text.


=====================================================================
6. BATCH PROCESSING (FOLDER → JSON)
=====================================================================

Run this script:

      python tools/batch_detect_to_json.py --input ./images --output result.json

Creates a JSON file containing detections for ALL images in a folder.

Example output:

{
  "page1.png": {
      "signature": 2,
      "stamp": 1,
      "qr": 0,
      "detections": [...]
  },
  "page2.png": {
      ...
  }
}


=====================================================================
7. DOCUMENT VIEWER FEATURES (FRONTEND)
=====================================================================

The document viewer supports:

 - Mouse wheel zoom
 - Slider zoom
 - Click + drag panning
 - Colored bounding boxes:
        signature = green
        stamp     = blue
        qr        = pink
 - Clickable filters
 - Confidence slider
 - Page navigation arrows
 - High-quality image scaling


=====================================================================
8. DRAG & DROP UPLOAD
=====================================================================

Features:
 - Highlight on drag-over
 - File drop detection
 - Automatic upload
 - Loading spinner while analyzing
 - Error handling


=====================================================================
9. MODEL INFORMATION
=====================================================================

YOLOv8 model file:
      backend/models/best_yolo_raw.pt

Loads once at startup:
      model = YOLO("models/best_yolo_raw.pt")

You can replace with your own trained model.


=====================================================================
10. TROUBLESHOOTING
=====================================================================

• Frontend CORS issues:
  Ensure ports 5173 and 8000 are whitelisted in backend’s CORS settings.

• YOLO loads slowly:
  Move model to SSD or use lighter version.

• PDF does not show Cyrillic:
  Ensure Roboto-Regular.ttf and Roboto-Bold.ttf are installed.

• Report not downloading:
  Check backend/logs for path errors.


=====================================================================
11. FUTURE IMPROVEMENTS
=====================================================================

 - OCR text extraction
 - Sensitive information redaction
 - Additional detection classes
 - Model auto-updater
 - Cloud storage (S3 / Azure)
 - Docker deployment
 - Processing pipeline for large batches


=====================================================================
12. SUMMARY
=====================================================================

Armeta Inspector is a complete AI-powered solution for document
analysis, offering:

 - Full stack (FastAPI + React)
 - YOLO-based detection
 - Dark-themed PDF report
 - Drag & Drop interface
 - Zoom + pan viewer
 - Batch image processing
 - Confidence filtering
 - Cyrillic support
 - Logo integration
 - Per-page intelligent analysis

=====================================================================
End of README.txt
=====================================================================

