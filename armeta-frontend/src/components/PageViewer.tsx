import React, { useRef, useState } from "react";
import type { DetectionClass, PageResult } from "../types";

interface Props {
  page: PageResult;
  visibleClasses: DetectionClass[];
  minScore: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPrevPage: () => void;
  onNextPage: () => void;
}

export const PageViewer: React.FC<Props> = ({
  page,
  visibleClasses,
  minScore,
  hasPrev,
  hasNext,
  onPrevPage,
  onNextPage,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // локальный зум
  const [zoom, setZoom] = useState(1);

  // базовые размеры (когда картинка просто вписана)
  const [base, setBase] = useState({
    imgW: 0,
    imgH: 0,
    offsetX: 0,
    offsetY: 0,
  });

  // смещение при перетаскивании
  const [pan, setPan] = useState({ x: 0, y: 0 });

  // состояние драга
  const [drag, setDrag] = useState({
    active: false,
    startX: 0,
    startY: 0,
  });

  const handleImgLoad: React.ReactEventHandler<HTMLImageElement> = (e) => {
    const img = e.currentTarget;
    const cont = containerRef.current;
    if (!cont) return;

    const naturalW = img.naturalWidth;
    const naturalH = img.naturalHeight;
    const contW = cont.clientWidth;
    const contH = cont.clientHeight;

    const contRatio = contW / contH;
    const imgRatio = naturalW / naturalH;

    let imgW: number;
    let imgH: number;

    if (imgRatio > contRatio) {
      imgW = contW;
      imgH = contW / imgRatio;
    } else {
      imgH = contH;
      imgW = contH * imgRatio;
    }

    const offsetX = (contW - imgW) / 2;
    const offsetY = (contH - imgH) / 2;

    setBase({ imgW, imgH, offsetX, offsetY });
    setPan({ x: 0, y: 0 }); // при смене страницы/картинки сбрасываем панинг
  };

  const filtered = page.detections.filter(
    (d) => visibleClasses.includes(d.label) && d.score >= minScore
  );

  // масштабирование вокруг центра
  const scaledW = base.imgW * zoom;
  const scaledH = base.imgH * zoom;
  const centerOffsetX = base.offsetX + (base.imgW - scaledW) / 2;
  const centerOffsetY = base.offsetY + (base.imgH - scaledH) / 2;

  // итоговый оффсет с учётом перетаскивания
  const finalOffsetX = centerOffsetX + pan.x;
  const finalOffsetY = centerOffsetY + pan.y;

  // DRAG
  const handleMouseDown: React.MouseEventHandler<HTMLDivElement> = (e) => {
    if (e.button !== 0) return; // только ЛКМ
    setDrag({
      active: true,
      startX: e.clientX,
      startY: e.clientY,
    });
  };

  const handleMouseMove: React.MouseEventHandler<HTMLDivElement> = (e) => {
    if (!drag.active) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;

    setPan((prev) => ({
      x: prev.x + dx,
      y: prev.y + dy,
    }));

    setDrag({
      active: true,
      startX: e.clientX,
      startY: e.clientY,
    });
  };

  const stopDrag = () => {
    if (!drag.active) return;
    setDrag((prev) => ({ ...prev, active: false }));
  };

  const handleMouseUp: React.MouseEventHandler<HTMLDivElement> = () => {
    stopDrag();
  };

  const handleMouseLeave: React.MouseEventHandler<HTMLDivElement> = () => {
    stopDrag();
  };

  // 🔍 ZOOM КОЛЕСИКОМ
  const handleWheel: React.WheelEventHandler<HTMLDivElement> = (e) => {
    // чтобы страница не скроллилась
    e.preventDefault();

    const delta = e.deltaY;
    const step = 0.1; // размер шага зума

    setZoom((prev) => {
      const dir = delta > 0 ? -1 : 1; // колесо вниз — уменьшаем, вверх — увеличиваем
      let next = prev + dir * step;
      if (next < 0.5) next = 0.5;
      if (next > 2) next = 2;
      return next;
    });
  };

  // курсор "рука" при зуме > 1
  const containerCursor =
    zoom > 1
      ? drag.active
        ? "cursor-grabbing"
        : "cursor-grab"
      : "cursor-default";

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-slate-900 rounded-xl border border-slate-700 overflow-hidden ${containerCursor}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      onWheel={handleWheel}
    >
      {/* Картинка */}
      <img
        ref={imgRef}
        src={page.imageUrl}
        alt={`page-${page.pageIndex}`}
        onLoad={handleImgLoad}
        className="absolute select-none"
        draggable={false}
        style={{
          width: scaledW,
          height: scaledH,
          left: finalOffsetX,
          top: finalOffsetY,
        }}
      />

      {/* Боксы */}
      {scaledW > 0 &&
        filtered.map((det) => {
          const left = finalOffsetX + det.x * scaledW;
          const top = finalOffsetY + det.y * scaledH;
          const width = det.w * scaledW;
          const height = det.h * scaledH;

          const borderColor =
            det.label === "signature"
              ? "border-emerald-400"
              : det.label === "stamp"
              ? "border-sky-400"
              : "border-fuchsia-400";

          const bgColor =
            det.label === "signature"
              ? "bg-emerald-400/20"
              : det.label === "stamp"
              ? "bg-sky-400/20"
              : "bg-fuchsia-400/20";

          return (
            <div
              key={det.id}
              className={`absolute ${borderColor} ${bgColor} border-2 rounded-md shadow-[0_0_0_1px_rgba(15,23,42,0.9)] pointer-events-none`}
              style={{ left, top, width, height }}
            >
              <div className="absolute -top-6 left-0 text-xs px-1.5 py-0.5 rounded bg-slate-900/90 border border-slate-700 shadow">
                {det.label}{" "}
                <span className="text-slate-400">{det.score.toFixed(2)}</span>
              </div>
            </div>
          );
        })}

      {/* Стрелки перелистывания (останавливаем drag + колесо не мешает) */}
      {hasPrev && (
        <button
          type="button"
          onClick={onPrevPage}
          onMouseDown={(e) => e.stopPropagation()}
          className="absolute left-4 top-1/2 -translate-y-1/2
                     rounded-full bg-slate-900/60 hover:bg-slate-900/90
                     border border-slate-700 text-slate-100 px-2 py-2
                     shadow cursor-pointer"
        >
          ‹
        </button>
      )}

      {hasNext && (
        <button
          type="button"
          onClick={onNextPage}
          onMouseDown={(e) => e.stopPropagation()}
          className="absolute right-4 top-1/2 -translate-y-1/2
                     rounded-full bg-slate-900/60 hover:bg-slate-900/90
                     border border-slate-700 text-slate-100 px-2 py-2
                     shadow cursor-pointer"
        >
          ›
        </button>
      )}

      {/* Зум-контрол сверху справа (тоже не запускает drag) */}
      <div
        className="absolute top-4 right-4 flex flex-col items-center gap-2
                   bg-slate-900/70 border border-slate-700 rounded-2xl px-3 py-3
                   shadow-lg"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <span className="text-[10px] uppercase tracking-wide text-slate-400">
          Zoom
        </span>
        <input
          type="range"
          min={0.5}
          max={2}
          step={0.1}
          value={zoom}
          onChange={(e) => setZoom(parseFloat(e.target.value))}
          className="w-24 h-4 cursor-pointer"
        />
        <span className="text-[10px] text-slate-300">
          {Math.round(zoom * 100)}%
        </span>
      </div>
    </div>
  );
};
