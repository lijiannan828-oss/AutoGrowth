"use client";

import React, { useState } from "react";
import StickerEditor, { Sticker } from "@/components/sticker/StickerEditor";
import StickerPicker from "@/components/sticker/StickerPicker";
import { Sticker as StickerIcon, Download, Trash2, Image as ImageIcon } from "lucide-react";

export default function StickerEditorDemo() {
  const [stickers, setStickers] = useState<Sticker[]>([]);
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [backgroundImage, setBackgroundImage] = useState<string>("");
  const [showGrid, setShowGrid] = useState(true);

  const handleAddSticker = (stickerUrl: string) => {
    const newSticker: Sticker = {
      id: `sticker-${Date.now()}-${Math.random()}`,
      src: stickerUrl,
      x: 400 - 50,
      y: 300 - 50,
      width: 100,
      height: 100,
      rotation: 0,
      zIndex: stickers.length + 1,
    };
    setStickers([...stickers, newSticker]);
  };

  const handleClearAll = () => {
    if (confirm("确定要清空所有贴纸吗？")) {
      setStickers([]);
    }
  };

  const handleUploadBackground = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setBackgroundImage(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleExport = () => {
    alert("导出功能开发中...");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-4xl font-bold text-gray-900">
            🎨 贴纸编辑器
          </h1>
          <p className="text-gray-600">
            拖拽调整位置 · 拖动右下角调整大小 · 点击工具栏旋转和缩放
          </p>
        </div>

        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl bg-white p-4 shadow-lg">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setIsPickerOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-3 font-medium text-white shadow-md hover:from-purple-600 hover:to-pink-600"
            >
              <StickerIcon className="h-5 w-5" />
              添加贴纸
            </button>

            <label className="flex cursor-pointer items-center gap-2 rounded-lg border-2 border-gray-300 bg-white px-6 py-3 font-medium text-gray-700 hover:border-blue-500 hover:bg-blue-50">
              <ImageIcon className="h-5 w-5" />
              上传背景
              <input
                type="file"
                accept="image/*"
                onChange={handleUploadBackground}
                className="hidden"
              />
            </label>

            <label className="flex cursor-pointer items-center gap-2 rounded-lg border-2 border-gray-300 bg-white px-6 py-3 font-medium text-gray-700 hover:border-blue-500">
              <input
                type="checkbox"
                checked={showGrid}
                onChange={(e) => setShowGrid(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
              />
              显示网格
            </label>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleClearAll}
              disabled={stickers.length === 0}
              className="flex items-center gap-2 rounded-lg border-2 border-red-300 bg-white px-4 py-2 font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              清空
            </button>

            <button
              onClick={handleExport}
              className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 font-medium text-white hover:bg-blue-600"
            >
              <Download className="h-4 w-4" />
              导出
            </button>
          </div>
        </div>

        <div className="flex justify-center">
          <StickerEditor
            containerWidth={800}
            containerHeight={600}
            backgroundImage={backgroundImage}
            initialStickers={stickers}
            onStickersChange={setStickers}
            showGrid={showGrid}
          />
        </div>

        <div className="mt-6 rounded-xl bg-white p-4 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <span className="text-sm text-gray-600">贴纸数量</span>
                <p className="text-2xl font-bold text-gray-900">{stickers.length}</p>
              </div>
              <div className="h-12 w-px bg-gray-300" />
              <div>
                <span className="text-sm text-gray-600">画布大小</span>
                <p className="text-2xl font-bold text-gray-900">800 × 600</p>
              </div>
              <div className="h-12 w-px bg-gray-300" />
              <div>
                <span className="text-sm text-gray-600">背景图片</span>
                <p className="text-2xl font-bold text-gray-900">
                  {backgroundImage ? "已设置" : "未设置"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <StickerPicker
        isOpen={isPickerOpen}
        onClose={() => setIsPickerOpen(false)}
        onSelectSticker={handleAddSticker}
      />
    </div>
  );
}

