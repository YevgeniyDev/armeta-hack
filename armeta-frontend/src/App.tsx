import React, { useState } from "react";
import { analyzeDocument, downloadReport } from "./api";
import type { DocResult, DetectionClass } from "./types";
import { PageViewer } from "./components/PageViewer";
import logo from "./assets/favicon.png";

const ALL_CLASSES: DetectionClass[] = ["signature", "stamp", "qr"];

const App: React.FC = () => {
  const [docs, setDocs] = useState<DocResult[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [visibleClasses, setVisibleClasses] =
    useState<DetectionClass[]>(ALL_CLASSES);
  const [minScore, setMinScore] = useState(0.3);

  const selectedDoc =
    docs.find((d) => d.id === selectedDocId) ?? docs[0] ?? null;
  const selectedPage =
    selectedDoc?.pages.find((p) => p.pageIndex === selectedPageIndex) ??
    selectedDoc?.pages[0] ??
    null;

  const currentPagePos =
    selectedDoc && selectedPage
      ? selectedDoc.pages.findIndex(
          (p) => p.pageIndex === selectedPage.pageIndex
        )
      : -1;

  const hasPrev = selectedDoc && currentPagePos > 0;
  const hasNext =
    selectedDoc &&
    currentPagePos >= 0 &&
    currentPagePos < selectedDoc.pages.length - 1;

  const goPrevPage = () => {
    if (!selectedDoc || currentPagePos <= 0) return;
    const prevPage = selectedDoc.pages[currentPagePos - 1];
    setSelectedPageIndex(prevPage.pageIndex);
  };

  const goNextPage = () => {
    if (!selectedDoc || !selectedDoc.pages.length) return;
    if (currentPagePos < 0 || currentPagePos >= selectedDoc.pages.length - 1)
      return;
    const nextPage = selectedDoc.pages[currentPagePos + 1];
    setSelectedPageIndex(nextPage.pageIndex);
  };

  // -------- common file processing (upload or drop) ----------
  const processFile = async (file: File) => {
    setIsUploading(true);
    try {
      const result = await analyzeDocument(file);
      setDocs((prev) => [result, ...prev]);
      setSelectedDocId(result.id);
      setSelectedPageIndex(result.pages[0]?.pageIndex ?? 0);
    } catch (err) {
      console.error(err);
      alert("Failed to analyze document");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = async (
    e
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processFile(file);
    e.target.value = "";
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // leave only when actually leaving the drop container
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    await processFile(file);
  };

  const toggleClass = (cls: DetectionClass) => {
    setVisibleClasses((prev) =>
      prev.includes(cls) ? prev.filter((c) => c !== cls) : [...prev, cls]
    );
  };

  const handleDownloadReport = async () => {
    if (!selectedDoc) return;
    try {
      await downloadReport(selectedDoc.id, selectedDoc.filename);
    } catch (err) {
      console.error(err);
      alert("Failed to download report");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="flex items-center gap-3">
          {/* LOGO */}
          <div className="h-8 w-8 rounded-lg overflow-hidden bg-emerald-500 flex items-center justify-center">
            <img
              src={logo}
              alt="Armeta logo"
              className="h-7 w-7 object-contain"
            />
          </div>
          <div>
            <div className="font-semibold leading-tight text-sm">
              Armeta Inspector
            </div>
            <div className="text-xs text-slate-400">
              Signatures · Stamps · QR codes
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Download report */}
          <button
            type="button"
            onClick={handleDownloadReport}
            disabled={!selectedDoc || isUploading}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900 text-xs font-medium text-slate-100 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Download report
          </button>

          {/* Upload button */}
          <label className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 text-xs font-medium hover:bg-emerald-400 cursor-pointer disabled:opacity-50">
            <input
              type="file"
              accept=".pdf,image/*"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
            {isUploading ? "Processing..." : "Upload document"}
          </label>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: documents */}
        <aside className="w-64 border-r border-slate-800 bg-slate-950/80 px-3 py-3 flex flex-col gap-3">
          <h2 className="text-xs uppercase tracking-wide text-slate-500 mb-1">
            Documents
          </h2>
          <div className="flex-1 space-y-1 overflow-auto">
            {docs.length === 0 && (
              <div className="text-xs text-slate-500">
                No documents yet. Upload a PDF or image to get started.
              </div>
            )}
            {docs.map((doc) => (
              <button
                key={doc.id}
                onClick={() => {
                  setSelectedDocId(doc.id);
                  setSelectedPageIndex(doc.pages[0]?.pageIndex ?? 0);
                }}
                className={`w-full text-left px-2 py-1.5 rounded-md text-xs border border-transparent hover:border-slate-700 ${
                  doc.id === selectedDoc?.id
                    ? "bg-slate-800 border-slate-700"
                    : "bg-slate-900"
                }`}
              >
                <div className="truncate">{doc.filename}</div>
                <div className="text-[11px] text-slate-500">
                  {doc.pages.length} page(s)
                </div>
              </button>
            ))}
          </div>

          {selectedDoc && (
            <div className="mt-2">
              <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-1">
                Pages
              </h3>
              <div className="flex flex-wrap gap-1">
                {selectedDoc.pages.map((p) => (
                  <button
                    key={p.pageIndex}
                    onClick={() => setSelectedPageIndex(p.pageIndex)}
                    className={`px-2 py-1 rounded text-xs border ${
                      p.pageIndex === selectedPageIndex
                        ? "bg-slate-800 border-emerald-400"
                        : "bg-slate-900 border-slate-700"
                    }`}
                  >
                    {p.pageIndex + 1}
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Center: page viewer / drop zone */}
        <main className="flex-1 flex flex-col items-stretch justify-center px-4 py-4 gap-3">
          {selectedDoc && selectedPage ? (
            <PageViewer
              page={selectedPage}
              visibleClasses={visibleClasses}
              minScore={minScore}
              hasPrev={!!hasPrev}
              hasNext={!!hasNext}
              onPrevPage={goPrevPage}
              onNextPage={goNextPage}
            />
          ) : (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className="flex-1 flex items-center justify-center"
            >
              {isUploading ? (
                // Loading state while backend analyzes the dropped/uploaded file
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                  <p className="text-slate-300 text-sm">
                    Analyzing document...
                  </p>
                </div>
              ) : (
                // Normal drop zone
                <div
                  className={`max-w-xl w-full h-64 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center transition-colors
                    ${
                      isDragging
                        ? "border-emerald-400 bg-emerald-500/10"
                        : "border-slate-700 bg-slate-900/40"
                    }`}
                >
                  <p className="text-sm font-medium">
                    Drop a PDF or image here
                  </p>
                  <p className="text-xs text-slate-400 mt-2">
                    …or click{" "}
                    <span className="font-semibold">Upload document</span> in
                    the top-right corner
                  </p>
                  <p className="text-[11px] text-slate-500 mt-3">
                    Supported: PDF, PNG, JPG, JPEG, TIFF, BMP
                  </p>
                </div>
              )}
            </div>
          )}
        </main>

        {/* Right sidebar: filters & detections */}
        <aside className="w-72 border-l border-slate-800 bg-slate-950/80 px-4 py-4 flex flex-col gap-4">
          <div>
            <h2 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
              Filters
            </h2>
            <div className="space-y-2">
              {/* CLASS FILTERS */}
              <div className="flex flex-wrap gap-2">
                {ALL_CLASSES.map((cls) => {
                  const active = visibleClasses.includes(cls);
                  const label =
                    cls === "signature"
                      ? "Signature"
                      : cls === "stamp"
                      ? "Stamp"
                      : "QR code";
                  const color =
                    cls === "signature"
                      ? "bg-emerald-500/20 border-emerald-400 text-emerald-200"
                      : cls === "stamp"
                      ? "bg-sky-500/20 border-sky-400 text-sky-200"
                      : "bg-fuchsia-500/20 border-fuchsia-400 text-fuchsia-200";

                  return (
                    <button
                      key={cls}
                      onClick={() => toggleClass(cls)}
                      className={`px-2 py-1 rounded-full text-xs border ${
                        active
                          ? color
                          : "bg-slate-900 border-slate-700 text-slate-400"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>

              {/* MIN CONFIDENCE */}
              <div className="mt-3">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Min confidence</span>
                  <span>{minScore.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={minScore}
                  onChange={(e) => setMinScore(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          {/* DETECTIONS LIST */}
          <div className="flex-1 overflow-auto">
            <h2 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
              Detections
            </h2>
            {selectedPage ? (
              <div className="space-y-1 text-xs">
                {selectedPage.detections
                  .filter(
                    (d) =>
                      visibleClasses.includes(d.label) && d.score >= minScore
                  )
                  .map((d) => (
                    <div
                      key={d.id}
                      className="border border-slate-700 rounded-md px-2 py-1 bg-slate-900"
                    >
                      <div className="flex justify-between">
                        <span className="font-medium">
                          {d.label === "signature"
                            ? "Signature"
                            : d.label === "stamp"
                            ? "Stamp"
                            : "QR code"}
                        </span>
                        <span className="text-slate-400">
                          {d.score.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        x={d.x.toFixed(2)}, y={d.y.toFixed(2)}, w=
                        {d.w.toFixed(2)}, h={d.h.toFixed(2)}
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500">
                No page selected yet.
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default App;
