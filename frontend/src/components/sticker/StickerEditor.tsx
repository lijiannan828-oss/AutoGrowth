"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, PanInfo } from "framer-motion";
import { X, RotateCw, ZoomIn, ZoomOut, Trash2 } from "lucide-react";

/**
 * 贴纸数据类型
 */
export interface Sticker {
  id: string;
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  zIndex: number;
}

/**
 * 贴纸编辑器属性
 */
interface StickerEditorProps {
  containerWidth?: number;
  containerHeight?: number;
  backgroundImage?: string;
  initialStickers?: Sticker[];
  onStickersChange?: (stickers: Sticker[]) => void;
  showGrid?: boolean;
  readOnly?: boolean;
}

/**
 * 可拖拽、可调整大小的贴纸编辑器
 */
export default function StickerEditor({
  containerWidth = 800,
  containerHeight = 600,
  backgroundImage,
  initialStickers = [],
  onStickersChange,
  showGrid = false,
  readOnly = false,
}: StickerEditorProps) {
  const [stickers, setStickers] = useState<Sticker[]>(initialStickers);
  const [selectedStickerId, setSelectedStickerId] = useState<string | null>(null);
  const [maxZIndex, setMaxZIndex] = useState(initialStickers.length);

  useEffect(() => {
    onStickersChange?.(stickers);
  }, [stickers, onStickersChange]);

  const deleteSticker = (id: string) => {
    setStickers(stickers.filter((s) => s.id !== id));
    if (selectedStickerId === id) {
      setSelectedStickerId(null);
    }
  };

  const updateStickerPosition = (id: string, x: number, y: number) => {
    setStickers(
      stickers.map((s) =>
        s.id === id ? { ...s, x, y, zIndex: maxZIndex + 1 } : s
      )
    );
    setMaxZIndex(maxZIndex + 1);
  };

  const updateStickerSize = (id: string, width: number, height: number) => {
    setStickers(
      stickers.map((s) => (s.id === id ? { ...s, width, height } : s))
    );
  };

  const rotateSticker = (id: string, delta: number = 15) => {
    setStickers(
      stickers.map((s) =>
        s.id === id ? { ...s, rotation: (s.rotation + delta) % 360 } : s
      )
    );
  };

  const scaleSticker = (id: string, scale: number) => {
    setStickers(
      stickers.map((s) =>
        s.id === id
          ? {
              ...s,
              width: Math.max(30, s.width * scale),
              height: Math.max(30, s.height * scale),
            }
          : s
      )
    );
  };

  const selectSticker = (id: string) => {
    setSelectedStickerId(id);
    setStickers(
      stickers.map((s) =>
        s.id === id ? { ...s, zIndex: maxZIndex + 1 } : s
      )
    );
    setMaxZIndex(maxZIndex + 1);
  };

  return (
    <div className="flex flex-col gap-4">
      <div
        className="relative overflow-hidden rounded-lg border-2 border-gray-300 bg-white shadow-lg"
        style={{
          width: containerWidth,
          height: containerHeight,
          backgroundImage: backgroundImage ? `url(${backgroundImage})` : undefined,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            setSelectedStickerId(null);
          }
        }}
      >
        {showGrid && (
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              backgroundImage: `
                linear-gradient(to right, rgba(0,0,0,0.05) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(0,0,0,0.05) 1px, transparent 1px)
              `,
              backgroundSize: "20px 20px",
            }}
          />
        )}

        {stickers.map((sticker) => (
          <StickerItem
            key={sticker.id}
            sticker={sticker}
            isSelected={selectedStickerId === sticker.id}
            readOnly={readOnly}
            onSelect={() => selectSticker(sticker.id)}
            onDrag={(x: number, y: number) => updateStickerPosition(sticker.id, x, y)}
            onResize={(width:number, height:number) => updateStickerSize(sticker.id, width, height)}
            onDelete={() => deleteSticker(sticker.id)}
          />
        ))}
      </div>

      {!readOnly && selectedStickerId && (
        <StickerToolbar
          sticker={stickers.find((s) => s.id === selectedStickerId)!}
          onRotate={() => rotateSticker(selectedStickerId)}
          onScaleUp={() => scaleSticker(selectedStickerId, 1.1)}
          onScaleDown={() => scaleSticker(selectedStickerId, 0.9)}
          onDelete={() => deleteSticker(selectedStickerId)}
        />
      )}
    </div>
  );
}

function StickerItem({
  sticker,
  isSelected,
  readOnly,
  onSelect,
  onDrag,
  onResize,
  onDelete,
}: any) {
  const [isResizing, setIsResizing] = useState(false);

  const handleDrag = (event: any, info: PanInfo) => {
    if (readOnly) return;
    const newX = sticker.x + info.delta.x;
    const newY = sticker.y + info.delta.y;
    onDrag(newX, newY);
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    if (readOnly) return;
    e.stopPropagation();
    setIsResizing(true);

    const startX = e.clientX;
    const startY = e.clientY;
    const startWidth = sticker.width;
    const startHeight = sticker.height;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;
      const newWidth = Math.max(30, startWidth + deltaX);
      const newHeight = Math.max(30, startHeight + deltaY);
      onResize(newWidth, newHeight);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  return (
    <motion.div
      drag={!readOnly}
      dragMomentum={false}
      onDrag={handleDrag}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      className={`absolute cursor-move select-none ${
        isSelected ? "ring-2 ring-blue-500 ring-offset-2" : ""
      }`}
      style={{
        left: sticker.x,
        top: sticker.y,
        width: sticker.width,
        height: sticker.height,
        transform: `rotate(${sticker.rotation}deg)`,
        zIndex: sticker.zIndex,
      }}
      whileHover={{ scale: readOnly ? 1 : 1.05 }}
      whileTap={{ scale: readOnly ? 1 : 0.95 }}
    >
      <img
        src={sticker.src}
        alt="sticker"
        className="h-full w-full object-contain pointer-events-none"
        draggable={false}
      />

      {isSelected && !readOnly && (
        <>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 text-white shadow-lg hover:bg-red-600"
          >
            <X className="h-3 w-3" />
          </button>

          <div
            onMouseDown={handleResizeStart}
            className="absolute -bottom-2 -right-2 h-4 w-4 cursor-nwse-resize rounded-full bg-blue-500 shadow-lg hover:bg-blue-600"
          />
        </>
      )}
    </motion.div>
  );
}

function StickerToolbar({ sticker, onRotate, onScaleUp, onScaleDown, onDelete }: any) {
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-white p-3 shadow-md">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">选中贴纸:</span>
        <img src={sticker.src} alt="selected" className="h-8 w-8 rounded object-contain" />
      </div>

      <div className="mx-2 h-6 w-px bg-gray-300" />

      <button
        onClick={onRotate}
        className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-100"
      >
        <RotateCw className="h-4 w-4" />
        旋转
      </button>

      <button
        onClick={onScaleUp}
        className="flex items-center gap-1 rounded-md bg-green-50 px-3 py-2 text-sm font-medium text-green-600 hover:bg-green-100"
      >
        <ZoomIn className="h-4 w-4" />
        放大
      </button>

      <button
        onClick={onScaleDown}
        className="flex items-center gap-1 rounded-md bg-orange-50 px-3 py-2 text-sm font-medium text-orange-600 hover:bg-orange-100"
      >
        <ZoomOut className="h-4 w-4" />
        缩小
      </button>

      <button
        onClick={onDelete}
        className="flex items-center gap-1 rounded-md bg-red-50 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-100"
      >
        <Trash2 className="h-4 w-4" />
        删除
      </button>

      <div className="mx-2 h-6 w-px bg-gray-300" />

      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>位置: ({Math.round(sticker.x)}, {Math.round(sticker.y)})</span>
        <span>大小: {Math.round(sticker.width)} × {Math.round(sticker.height)}</span>
        <span>旋转: {sticker.rotation}°</span>
      </div>
    </div>
  );
}

