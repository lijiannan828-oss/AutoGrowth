"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, X, Search, Grid3x3, List } from "lucide-react";

export interface StickerCategory {
  id: string;
  name: string;
  icon: string;
  stickers: string[];
}

interface StickerPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSticker: (stickerUrl: string) => void;
  categories?: StickerCategory[];
}

const DEFAULT_CATEGORIES: StickerCategory[] = [
  {
    id: "cute_animals",
    name: "🐱 可爱动物",
    icon: "🐱",
    stickers: [
      "/stickers/cute_animals/cat_wave.gif",
      "/stickers/cute_animals/cat_typing.gif",
      "/stickers/cute_animals/dog_happy.gif",
    ],
  },
  {
    id: "emoji",
    name: "😀 Emoji",
    icon: "😀",
    stickers: [
      "/stickers/emoji/cool.png",
      "/stickers/emoji/fire.png",
      "/stickers/emoji/heart.png",
    ],
  },
];

export default function StickerPicker({
  isOpen,
  onClose,
  onSelectSticker,
  categories = DEFAULT_CATEGORIES,
}: StickerPickerProps) {
  const [selectedCategory, setSelectedCategory] = useState(categories[0]?.id);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const currentCategory = categories.find((c) => c.id === selectedCategory);
  const filteredStickers = currentCategory?.stickers.filter((sticker) =>
    sticker.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const selectRandomSticker = () => {
    const allStickers = categories.flatMap((c) => c.stickers);
    const randomSticker = allStickers[Math.floor(Math.random() * allStickers.length)];
    onSelectSticker(randomSticker);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-4xl -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white shadow-2xl"
          >
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

                <button
                  onClick={onClose}
                  className="rounded-lg p-2 text-gray-600 hover:bg-gray-100"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

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

            <div className="flex h-[500px]">
              <div className="w-48 border-r bg-gray-50 p-2">
                <div className="space-y-1">
                  {categories.map((category) => (
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
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {filteredStickers.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-gray-400">
                    <div className="text-center">
                      <p className="text-lg font-medium">没有找到贴纸</p>
                    </div>
                  </div>
                ) : (
                  <div
                    className={
                      viewMode === "grid"
                        ? "grid grid-cols-4 gap-4"
                        : "space-y-2"
                    }
                  >
                    {filteredStickers.map((sticker, index) => (
                      <motion.button
                        key={sticker}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.02 }}
                        onClick={() => {
                          onSelectSticker(sticker);
                          onClose();
                        }}
                        className={`group relative overflow-hidden rounded-lg border-2 border-transparent bg-gray-50 transition-all hover:border-blue-500 hover:shadow-lg ${
                          viewMode === "grid"
                            ? "aspect-square p-4"
                            : "flex items-center gap-3 p-3"
                        }`}
                      >
                        <img
                          src={sticker}
                          alt="sticker"
                          className={`object-contain ${
                            viewMode === "grid"
                              ? "h-full w-full"
                              : "h-12 w-12"
                          }`}
                        />
                      </motion.button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="border-t bg-gray-50 p-3 text-center text-xs text-gray-500">
              💡 提示：点击贴纸添加到画布，拖拽调整位置，拖动右下角调整大小
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

