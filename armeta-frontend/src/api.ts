import type { DocResult } from "./types";

// базовый URL бэкенда — для локалки
const BACKEND_URL = "http://127.0.0.1:8000";

export async function analyzeDocument(file: File): Promise<DocResult> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BACKEND_URL}/analyze`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`API error: ${res.status} ${msg}`);
  }

  const data = (await res.json()) as DocResult;
  return data;
}

export async function downloadReport(docId: string, filename: string) {
  const res = await fetch(`http://127.0.0.1:8000/docs/${docId}/report`);

  if (!res.ok) {
    throw new Error(`Failed to download report: ${res.status}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.replace(/\.pdf$/i, "") + "_report.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
