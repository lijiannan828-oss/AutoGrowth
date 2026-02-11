"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Search, Grid3x3, List, Sparkles } from "lucide-react";
import { STICKER_CATEGORIES, StickerItem } from "@/lib/sticker-config";

interface ImageStickerPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSticker: (stickerPath: string) => void;
}

/**
 * 图片贴纸选择器
 */
export default function ImageStickerPicker({
  isOpen,
  onClose,
  onSelectSticker,
}: ImageStickerPickerProps) {
  const [selectedCategory, setSelectedCategory] = useState(STICKER_CATEGORIES[0]?.id);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const currentCategory = STICKER_CATEGORIES.find((c) => c.id === selectedCategory);
  const filteredStickers = currentCategory?.stickers.filter((sticker) =>
    sticker.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const selectRandomSticker = () => {
    const allStickers = STICKER_CATEGORIES.flatMap((c) => c.stickers);
    const randomSticker = allStickers[Math.floor(Math.random() * allStickers.length)];
    onSelectSticker(randomSticker.path);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* 遮罩层 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />

          {/* 面板 */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-5xl -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white shadow-2xl"
          >
            {/* 头部 */}
            <div className="flex items-center justify-between border-b p-4">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-gray-900">选择贴纸</h2>
                <button
                  onClick={selectRandomSticker}
                  className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2 text-sm font-medium text-white hover:from-purple-600 hover:to-pink-600"
                >
                  <Sparkles className="h-4 w-4" />
                  随机选择
                </button>
              </div>

              <div className="flex items-center gap-2">
                {/* 视图切换 */}
                <div className="flex rounded-lg border">
                  <button
                    onClick={() => setViewMode("grid")}
                    className={`p-2 ${
                      viewMode === "grid"
                        ? "bg-blue-50 text-blue-600"
                        : "text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <Grid3x3 className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setViewMode("list")}
                    className={`p-2 ${
                      viewMode === "list"
                        ? "bg-blue-50 text-blue-600"
                        : "text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <List className="h-4 w-4" />
                  </button>
                </div>

                {/* 关闭按钮 */}
                <button
                  onClick={onClose}
                  className="rounded-lg p-2 text-gray-600 hover:bg-gray-100"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* 搜索栏 */}
            <div className="border-b p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索贴纸..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
            </div>

            {/* 内容区域 */}
            <div className="flex h-[500px]">
              {/* 左侧类别列表 */}
              <div className="w-48 border-r bg-gray-50 p-2 overflow-y-auto">
                <div className="space-y-1">
                  {STICKER_CATEGORIES.map((category) => (
                    <button
                      key={category.id}
                      onClick={() => setSelectedCategory(category.id)}
                      className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                        selectedCategory === category.id
                          ? "bg-blue-500 text-white"
                          : "text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      <span className="text-lg">{category.icon}</span>
                      <span className="flex-1 truncate">{category.name}</span>
                      <span className="text-xs opacity-70">
                        {category.stickers.length}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 右侧贴纸网格 */}
              <div className="flex-1 overflow-y-auto p-4">
                {filteredStickers.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-gray-400">
                    <div className="text-center">
                      <p className="text-lg font-medium">没有找到贴纸</p>
                      <p className="text-sm">试试其他关键词</p>
                    </div>
                  </div>
                ) : (
                  <div
                    className={
                      viewMode === "grid"
                        ? "grid grid-cols-5 gap-4"
                        : "space-y-2"
                    }
                  >
                    {filteredStickers.map((sticker, index) => (
                      <motion.button
                        key={sticker.id}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.02 }}
                        onClick={() => {
                          onSelectSticker(sticker.path);
                          onClose();
                        }}
                        className={`group relative overflow-hidden rounded-lg border-2 border-transparent bg-gray-50 transition-all hover:border-blue-500 hover:shadow-lg ${
                          viewMode === "grid"
                            ? "aspect-square p-3"
                            : "flex items-center gap-3 p-3"
                        }`}
                      >
                        <img
                          src={sticker.path}
                          alt={sticker.name}
                          className={`object-contain ${
                            viewMode === "grid"
                              ? "h-full w-full"
                              : "h-12 w-12"
                          }`}
                        />
                        {viewMode === "list" && (
                          <span className="flex-1 truncate text-left text-sm text-gray-700">
                            {sticker.name}
                          </span>
                        )}
                        <div className="absolute inset-0 bg-blue-500/10 opacity-0 transition-opacity group-hover:opacity-100" />
                      </motion.button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 底部提示 */}
            <div className="border-t bg-gray-50 p-3 text-center text-xs text-gray-500">
              💡 提示：点击贴纸添加到画布，拖拽调整位置，点击旋转按钮调整角度
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

