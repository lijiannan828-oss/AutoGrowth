'use client';

import React, { useState } from 'react';
import { Play, Settings } from 'lucide-react';

export default function FissionDemoPage() {
  const [sourceVideo, setSourceVideo] = useState('');
  const [dramaName, setDramaName] = useState('');
  const [variantCount, setVariantCount] = useState(5);
  const [transforms, setTransforms] = useState({
    filter: { enabled: true, preset: 'warm' },
    duration: { enabled: true },
    shuffle: { enabled: false, intensity: 0.3 },
    sticker: { enabled: false }
  });

  const handleSubmit = () => {
    const config = {
      source_video_path: sourceVideo,
      drama_name: dramaName,
      variant_count: variantCount,
      transforms: [
        transforms.filter.enabled && { type: 'filter', enabled: true, params: { preset: transforms.filter.preset } },
        transforms.duration.enabled && { type: 'duration_adjust', enabled: true, params: {} },
        transforms.shuffle.enabled && { type: 'frame_shuffle', enabled: true, params: { intensity: transforms.shuffle.intensity } },
        transforms.sticker.enabled && { type: 'sticker_overlay', enabled: true, params: {} },
      ].filter(Boolean)
    };

    console.log('任务配置:', config);
    alert('任务配置已生成！\n\n请查看浏览器控制台（F12）查看完整配置。\n\n在生产环境中，这会调用API创建任务。');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-4xl mx-auto">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🎬 AI 裂变素材生成系统
          </h1>
          <p className="text-gray-600">
            快速批量产出差异化短剧素材，规避平台重复/撞审风险
          </p>
        </div>

        {/* 主表单 */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <Settings className="text-blue-600" />
            创建裂变任务
          </h2>

          {/* 基本信息 */}
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                源视频路径
              </label>
              <input
                type="text"
                value={sourceVideo}
                onChange={(e) => setSourceVideo(e.target.value)}
                placeholder="gs://bucket/path/to/video.mp4"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                剧集名称
              </label>
              <input
                type="text"
                value={dramaName}
                onChange={(e) => setDramaName(e.target.value)}
                placeholder="输入剧集名称"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                生成变体数量: <span className="text-blue-600 font-bold">{variantCount}</span>
              </label>
              <input
                type="range"
                min="5"
                max="20"
                value={variantCount}
                onChange={(e) => setVariantCount(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>5个</span>
                <span>20个</span>
              </div>
            </div>
          </div>

          {/* 变换配置 */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-semibold mb-4">变换配置</h3>
            
            <div className="space-y-4">
              {/* 滤镜 */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <input
                    type="checkbox"
                    checked={transforms.filter.enabled}
                    onChange={(e) => setTransforms({...transforms, filter: {...transforms.filter, enabled: e.target.checked}})}
                    className="w-5 h-5 text-blue-600 rounded"
                  />
                  <span className="font-medium text-gray-800">滤镜效果</span>
                </div>
                {transforms.filter.enabled && (
                  <select
                    value={transforms.filter.preset}
                    onChange={(e) => setTransforms({...transforms, filter: {...transforms.filter, preset: e.target.value}})}
                    className="ml-8 px-4 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="warm">🌅 暖色调</option>
                    <option value="cool">❄️ 冷色调</option>
                    <option value="vintage">📷 复古</option>
                    <option value="high_contrast">⚡ 高对比度</option>
                    <option value="soft">🌸 柔和</option>
                  </select>
                )}
              </div>

              {/* 时长调整 */}
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={transforms.duration.enabled}
                    onChange={(e) => setTransforms({...transforms, duration: {...transforms.duration, enabled: e.target.checked}})}
                    className="w-5 h-5 text-green-600 rounded"
                  />
                  <span className="font-medium text-gray-800">时长调整</span>
                  <span className="text-sm text-gray-600">(±20%浮动)</span>
                </div>
              </div>

              {/* 抽帧重组 */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <input
                    type="checkbox"
                    checked={transforms.shuffle.enabled}
                    onChange={(e) => setTransforms({...transforms, shuffle: {...transforms.shuffle, enabled: e.target.checked}})}
                    className="w-5 h-5 text-purple-600 rounded"
                  />
                  <span className="font-medium text-gray-800">抽帧重组</span>
                </div>
                {transforms.shuffle.enabled && (
                  <div className="ml-8">
                    <label className="text-sm text-gray-600">
                      强度: {transforms.shuffle.intensity}
                    </label>
                    <input
                      type="range"
                      min="0.1"
                      max="0.5"
                      step="0.1"
                      value={transforms.shuffle.intensity}
                      onChange={(e) => setTransforms({...transforms, shuffle: {...transforms.shuffle, intensity: parseFloat(e.target.value)}})}
                      className="w-full h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>轻度</span>
                      <span>重度</span>
                    </div>
                  </div>
                )}
              </div>

              {/* 贴纸叠加 */}
              <div className="bg-yellow-50 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={transforms.sticker.enabled}
                    onChange={(e) => setTransforms({...transforms, sticker: {...transforms.sticker, enabled: e.target.checked}})}
                    className="w-5 h-5 text-yellow-600 rounded"
                  />
                  <span className="font-medium text-gray-800">贴纸叠加</span>
                </div>
              </div>
            </div>
          </div>

          {/* 提交按钮 */}
          <button
            onClick={handleSubmit}
            className="w-full mt-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 text-lg font-semibold shadow-lg"
          >
            <Play size={24} />
            创建裂变任务
          </button>
        </div>

        {/* 功能说明 */}
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <h3 className="text-lg font-semibold mb-4">✨ 功能说明</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-blue-600 mb-2">🎨 滤镜效果</h4>
              <p className="text-gray-600">5种预设滤镜，改变视频色调</p>
            </div>
            <div>
              <h4 className="font-medium text-green-600 mb-2">⏱️ 时长调整</h4>
              <p className="text-gray-600">±20%时长浮动，规避检测</p>
            </div>
            <div>
              <h4 className="font-medium text-purple-600 mb-2">🎞️ 抽帧重组</h4>
              <p className="text-gray-600">智能抽帧，保持连贯性</p>
            </div>
            <div>
              <h4 className="font-medium text-yellow-600 mb-2">🏷️ 贴纸叠加</h4>
              <p className="text-gray-600">添加品牌标识或特效</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

