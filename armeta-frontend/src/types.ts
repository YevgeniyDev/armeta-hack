export type DetectionClass = "signature" | "stamp" | "qr";

export interface Detection {
  id: string;
  label: DetectionClass;
  score: number;
  // нормализованные координаты [0,1] относительно ширины/высоты
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PageResult {
  pageIndex: number;
  imageUrl: string; // URL страницы (PNG/JPEG)
  detections: Detection[];
}

export interface DocResult {
  id: string;
  filename: string;
  pages: PageResult[];
}
