"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { X, RotateCw } from "lucide-react";

/**
 * 单个贴纸数据
 */
export interface StickerData {
  id: string;
  content: string;
  x: number;
  y: number;
  size: number;
  rotation: number;
  isImage?: boolean;  // 是否为图片贴纸
  imagePath?: string; // 图片路径
  startTime?: number; // 贴纸开始显示时间（秒）
  endTime?: number;   // 贴纸结束显示时间（秒），-1表示到视频结束
}

/**
 * 多贴纸编辑器 - 支持多个贴纸同时编辑
 */
interface MultiStickerEditorProps {
  /** 视频预览宽度 */
  width: number;
  /** 视频预览高度 */
  height: number;
  /** 贴纸列表 */
  stickers: StickerData[];
  /** 贴纸变化回调 */
  onStickersChange: (stickers: StickerData[]) => void;
  /** 是否启用编辑 */
  enabled: boolean;
}

export function MultiStickerEditor({
  width,
  height,
  stickers,
  onStickersChange,
  enabled,
}: MultiStickerEditorProps) {
  const [selectedStickerId, setSelectedStickerId] = useState<string | null>(null);

  // 更新贴纸位置
  const updateStickerPosition = (id: string, x: number, y: number) => {
    onStickersChange(
      stickers.map((s) => (s.id === id ? { ...s, x, y } : s))
    );
  };

  // 更新贴纸旋转
  const updateStickerRotation = (id: string, rotation: number) => {
    onStickersChange(
      stickers.map((s) => (s.id === id ? { ...s, rotation } : s))
    );
  };

  // 删除贴纸
  const deleteSticker = (id: string) => {
    onStickersChange(stickers.filter((s) => s.id !== id));
    if (selectedStickerId === id) {
      setSelectedStickerId(null);
    }
  };

  if (!enabled) return null;

  // 调试日志
  console.log('🎨 MultiStickerEditor rendering:', {
    enabled,
    stickerCount: stickers.length,
    stickers: stickers.map(s => ({
      id: s.id,
      isImage: s.isImage,
      imagePath: s.imagePath,
      content: s.content,
      x: s.x,
      y: s.y,
      size: s.size
    }))
  });

  return (
    <>
      {stickers.map((sticker) => {
        console.log('🎨 Rendering sticker:', sticker.id, sticker);
        return (
          <DraggableSticker
            key={sticker.id}
            sticker={sticker}
            isSelected={selectedStickerId === sticker.id}
            onSelect={() => setSelectedStickerId(sticker.id)}
            onPositionChange={(x, y) => updateStickerPosition(sticker.id, x, y)}
            onRotate={() => updateStickerRotation(sticker.id, (sticker.rotation + 15) % 360)}
            onDelete={() => deleteSticker(sticker.id)}
          />
        );
      })}
    </>
  );
}

/**
 * 可拖拽的单个贴纸
 */
interface DraggableStickerProps {
  sticker: StickerData;
  isSelected: boolean;
  onSelect: () => void;
  onPositionChange: (x: number, y: number) => void;
  onRotate: () => void;
  onDelete: () => void;
}

function DraggableSticker({
  sticker,
  isSelected,
  onSelect,
  onPositionChange,
  onRotate,
  onDelete,
}: DraggableStickerProps) {
  const [isDragging, setIsDragging] = useState(false);

  // 拖拽处理
  const handleDrag = (event: any, info: any) => {
    const containerRect = event.target.parentElement?.getBoundingClientRect();
    if (!containerRect) return;

    const newX = ((info.point.x - containerRect.left) / containerRect.width) * 100;
    const newY = ((info.point.y - containerRect.top) / containerRect.height) * 100;

    const clampedX = Math.max(0, Math.min(100, newX));
    const clampedY = Math.max(0, Math.min(100, newY));

    onPositionChange(clampedX, clampedY);
  };

  return (
    <motion.div
      drag
      dragMomentum={false}
      onDragStart={() => setIsDragging(true)}
      onDragEnd={() => setIsDragging(false)}
      onDrag={handleDrag}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      className={`absolute cursor-move select-none ${
        isSelected ? "ring-2 ring-blue-500 ring-offset-2" : ""
      }`}
      style={{
        left: `${sticker.x}%`,
        top: `${sticker.y}%`,
        width: sticker.isImage ? `${sticker.size}px` : 'auto',
        height: sticker.isImage ? `${sticker.size}px` : 'auto',
        fontSize: sticker.isImage ? undefined : `${sticker.size}px`,
        transform: `translate(-50%, -50%) rotate(${sticker.rotation}deg)`,
        zIndex: isSelected ? 20 : 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.95 }}
    >
      {/* 显示图片或文字贴纸 */}
      {sticker.isImage && sticker.imagePath ? (
        <img
          src={sticker.imagePath}
          alt="sticker"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            pointerEvents: 'none',
          }}
          draggable={false}
          onLoad={() => {
            console.log('✅ Sticker loaded:', sticker.imagePath);
          }}
          onError={(e) => {
            console.error('❌ Failed to load sticker:', sticker.imagePath);
            console.error('Sticker data:', sticker);
          }}
        />
      ) : (
        <div className="px-2 py-1 bg-white/90 rounded shadow-lg font-bold">
          {sticker.content}
        </div>
      )}

      {/* 选中时显示控制按钮 */}
      {isSelected && (
        <>
          {/* 删除按钮 */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 text-white shadow-lg hover:bg-red-600"
          >
            <X className="h-3 w-3" />
          </button>

          {/* 旋转按钮 */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRotate();
            }}
            className="absolute -left-2 -top-2 rounded-full bg-blue-500 p-1 text-white shadow-lg hover:bg-blue-600"
          >
            <RotateCw className="h-3 w-3" />
          </button>
        </>
      )}
    </motion.div>
  );
}

/**
 * 简化版单个贴纸编辑器（向后兼容）
 */
interface SimpleStickerEditorProps {
  width: number;
  height: number;
  stickerContent: string;
  position: { x: number; y: number };
  size: number;
  onPositionChange: (position: { x: number; y: number }) => void;
  enabled: boolean;
}

export default function SimpleStickerEditor({
  width,
  height,
  stickerContent,
  position,
  size,
  onPositionChange,
  enabled,
}: SimpleStickerEditorProps) {
  const stickers: StickerData[] = enabled
    ? [
        {
          id: "single",
          content: stickerContent,
          x: position.x,
          y: position.y,
          size,
          rotation: 0,
        },
      ]
    : [];

  const handleStickersChange = (newStickers: StickerData[]) => {
    if (newStickers.length > 0) {
      onPositionChange({ x: newStickers[0].x, y: newStickers[0].y });
    }
  };

  return (
    <MultiStickerEditor
      width={width}
      height={height}
      stickers={stickers}
      onStickersChange={handleStickersChange}
      enabled={enabled}
    />
  );
}

/**
 * 贴纸位置选择器 - 快速选择预设位置
 */
interface StickerPositionPickerProps {
  onSelect: (position: { x: number; y: number }) => void;
  currentPosition: { x: number; y: number };
}

export function StickerPositionPicker({
  onSelect,
  currentPosition,
}: StickerPositionPickerProps) {
  const positions = [
    { name: "左上", x: 10, y: 10 },
    { name: "右上", x: 90, y: 10 },
    { name: "左下", x: 10, y: 90 },
    { name: "右下", x: 90, y: 90 },
    { name: "居中", x: 50, y: 50 },
  ];

  return (
    <div className="flex gap-2 flex-wrap">
      {positions.map((pos) => {
        const isActive =
          Math.abs(currentPosition.x - pos.x) < 5 &&
          Math.abs(currentPosition.y - pos.y) < 5;

        return (
          <button
            key={pos.name}
            onClick={() => onSelect({ x: pos.x, y: pos.y })}
            className={`px-3 py-1 text-xs rounded border transition-colors ${
              isActive
                ? "bg-blue-500 text-white border-blue-500"
                : "bg-white text-gray-700 border-gray-300 hover:border-blue-500"
            }`}
          >
            {pos.name}
          </button>
        );
      })}
    </div>
  );
}

