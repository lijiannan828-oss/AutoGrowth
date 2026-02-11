'use client';

import React, { useState, useEffect, useRef } from 'react';
import apiClient from '@/lib/api-client';
import { MultiStickerEditor, StickerData } from '@/components/sticker/SimpleStickerEditor';
import ImageStickerPicker from '@/components/sticker/ImageStickerPicker';
import { getRandomStickerPath } from '@/lib/sticker-config';

interface Transform {
  type: 'filter' | 'frame_shuffle' | 'duration_adjust' | 'sticker_overlay';
  enabled: boolean;
  params: Record<string, any>;
}

interface FissionJob {
  job_id: string;
  drama_name: string;
  variant_count: number;
  status: string;
  progress: number;
  created_at: string;
  created_by: string;
  error_message?: string;  // 添加错误信息字段
}

interface Variant {
  variant_id: string;
  output_path: string;
  file_size_bytes: number;
  duration_seconds: number;
  transforms_applied: string[];
  thumbnail_path?: string;
}

// 获取贴纸显示内容的辅助函数
const getStickerContent = (stickerId: string): string => {
  const stickerMap: Record<string, string> = {
    'emoji_fire': '🔥',
    'emoji_heart': '❤️',
    'emoji_laugh': '😂',
    'emoji_love': '😍',
    'emoji_cool': '😎',
    'emoji_cry': '😭',
    'emoji_shock': '😱',
    'emoji_party': '🎉',
    'emoji_thumbsup': '👍',
    'emoji_clap': '👏',
    'emoji_muscle': '💪',
    'emoji_100': '💯',
    'emoji_star': '⭐',
    'emoji_sparkle': '✨',
    'emoji_crown': '👑',
    'emoji_diamond': '💎',
    'emoji_rocket': '🚀',
    'emoji_money': '💰',
    'meme_666': '666',
    'meme_yyds': 'YYDS',
    'meme_awsl': 'AWSL',
    'meme_omo': 'OMO',
    'meme_wow': 'WOW',
    'meme_omg': 'OMG',
    'meme_lol': 'LOL',
    'meme_绝绝子': '绝绝子',
    'meme_爱了': '爱了爱了',
    'meme_笑死': '笑死',
    'meme_绝了': '绝了',
    'tag_hot': '🔥HOT',
    'tag_new': '✨NEW',
    'tag_top': '👑TOP',
    'tag_vip': '💎VIP',
    'tag_best': '⭐BEST',
    'tag_like': '❤️LIKE',
    'tag_sale': '💰特惠',
    'tag_limited': '⏰限时',
  };
  return stickerMap[stickerId] || '🔥HOT';
};

// 所有可用的贴纸 ID
const ALL_STICKER_IDS = [
  'emoji_fire', 'emoji_heart', 'emoji_laugh', 'emoji_love', 'emoji_cool',
  'emoji_cry', 'emoji_shock', 'emoji_party', 'emoji_thumbsup', 'emoji_clap',
  'emoji_muscle', 'emoji_100', 'emoji_star', 'emoji_sparkle', 'emoji_crown',
  'emoji_diamond', 'emoji_rocket', 'emoji_money',
  'meme_666', 'meme_yyds', 'meme_awsl', 'meme_omo', 'meme_wow', 'meme_omg', 'meme_lol',
  'meme_绝绝子', 'meme_爱了', 'meme_笑死', 'meme_绝了',
  'tag_hot', 'tag_new', 'tag_top', 'tag_vip', 'tag_best', 'tag_like', 'tag_sale', 'tag_limited',
];

// 随机生成贴纸
const generateRandomSticker = (): StickerData => {
  const randomStickerId = ALL_STICKER_IDS[Math.floor(Math.random() * ALL_STICKER_IDS.length)];
  const randomX = Math.random() * 80 + 10; // 10-90%
  const randomY = Math.random() * 80 + 10; // 10-90%
  const randomSize = [20, 28, 32, 40, 48][Math.floor(Math.random() * 5)];
  const randomRotation = Math.floor(Math.random() * 360);

  return {
    id: `sticker-${Date.now()}-${Math.random()}`,
    content: getStickerContent(randomStickerId),
    x: randomX,
    y: randomY,
    size: randomSize,
    rotation: randomRotation,
  };
};

export default function FissionPage() {
  const [sourceVideo, setSourceVideo] = useState('');
  const [dramaName, setDramaName] = useState('');
  const [variantCount, setVariantCount] = useState(5);
  const [transforms, setTransforms] = useState<Transform[]>([
    { type: 'filter', enabled: true, params: { preset: 'warm' } },
    { type: 'duration_adjust', enabled: true, params: {} },
    { type: 'frame_shuffle', enabled: false, params: { intensity: 0.3 } },
    {
      type: 'sticker_overlay',
      enabled: false,
      params: {
        stickers: [] as StickerData[], // 多个贴纸列表
        start_time: 0,
        end_time: -1
      }
    },
  ]);
  const [jobs, setJobs] = useState<FissionJob[]>([]);
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  const [jobDetails, setJobDetails] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [gcsVideos, setGcsVideos] = useState<any[]>([]);

  // 新增：文字描述状态
  const [videoDescription, setVideoDescription] = useState('');
  const [inputMode, setInputMode] = useState<'upload' | 'text'>('upload'); // 输入模式：上传或文字描述

  // 图片贴纸选择器状态
  const [isImageStickerPickerOpen, setIsImageStickerPickerOpen] = useState(false);
  const [currentStickerTransformIndex, setCurrentStickerTransformIndex] = useState<number | null>(null);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalJobs, setTotalJobs] = useState(0);

  useEffect(() => {
    loadJobs();
    loadGcsVideos();
    const interval = setInterval(loadJobs, 5000); // 每5秒刷新
    return () => clearInterval(interval);
  }, [currentPage, pageSize]);

  const loadGcsVideos = async () => {
    try {
      const response = await apiClient.get('/fission/videos');
      setGcsVideos(response.data.videos || []);
    } catch (error) {
      console.error('Failed to load GCS videos:', error);
    }
  };

  const loadJobs = async () => {
    try {
      const response = await apiClient.get(`/fission/jobs?page=${currentPage}&page_size=${pageSize}`);
      setJobs(response.data.jobs || []);
      setTotalJobs(response.data.total || 0);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    }
  };

  const loadJobDetail = async (jobId: string) => {
    try {
      const response = await apiClient.get(`/fission/jobs/${jobId}`);
      setJobDetails(prev => ({ ...prev, [jobId]: response.data }));
    } catch (error) {
      console.error('Failed to load job detail:', error);
    }
  };

  const toggleJobDetail = async (jobId: string) => {
    const newExpandedJobs = new Set(expandedJobs);
    if (newExpandedJobs.has(jobId)) {
      // 收起详情
      newExpandedJobs.delete(jobId);
    } else {
      // 展开详情
      newExpandedJobs.add(jobId);
      // 如果还没有加载详情，则加载
      if (!jobDetails[jobId]) {
        await loadJobDetail(jobId);
      }
    }
    setExpandedJobs(newExpandedJobs);
  };

  const createJob = async () => {
    // 验证输入
    if (inputMode === 'upload') {
      if (!sourceVideo) {
        if (selectedFile && !uploading) {
          alert('请先点击“上传视频”按钮完成上传');
        } else {
          alert('请填写源视频路径或上传视频');
        }
        return;
      }
    } else {
      if (!videoDescription.trim()) {
        alert('请输入视频描述');
        return;
      }
    }

    if (!dramaName) {
      alert('请填写剧集名称');
      return;
    }

    setLoading(true);
    try {
      // 转换贴纸数据格式
      const convertedTransforms = transforms.map(transform => {
        if (transform.type === 'sticker_overlay' && transform.params.stickers) {
          // 将多个贴纸转换为多个 sticker_overlay transform
          const stickers = transform.params.stickers as StickerData[];

          // 如果有贴纸，返回多个 transform
          if (stickers.length > 0) {
            return stickers.map(sticker => ({
              type: 'sticker_overlay' as const,
              enabled: true,
              params: {
                // 如果是图片贴纸
                ...(sticker.isImage && sticker.imagePath ? {
                  image_path: sticker.imagePath,
                  sticker_id: 'custom_image',
                } : {
                  // 如果是文字贴纸
                  sticker_id: 'custom_text',
                  text: sticker.content,
                }),
                position: 'custom',
                // 传递百分比坐标，后端根据视频分辨率计算像素
                x_percent: sticker.x,
                y_percent: sticker.y,
                size: sticker.size,
                rotation: sticker.rotation,
                // 使用贴纸独立时间，如果没有则使用 transform 级别的时间
                start_time: sticker.startTime ?? transform.params.start_time ?? 0,
                end_time: sticker.endTime ?? transform.params.end_time ?? -1,
              }
            }));
          }
        }
        return transform;
      }).flat(); // 展平数组

      console.log('🎨 Converted transforms:', convertedTransforms);

      // 根据输入模式构建请求数据
      const requestData: any = {
        drama_name: dramaName,
        variant_count: variantCount,
        transforms: convertedTransforms,
        max_output_size_mb: 500,
        duration_variance_percent: 20,
      };

      if (inputMode === 'upload') {
        requestData.source_video_path = sourceVideo;
      } else {
        requestData.video_description = videoDescription;
        requestData.generation_mode = 'text_to_video';
      }

      await apiClient.post('/fission/jobs', requestData);

      alert('任务创建成功！');
      loadJobs();

      // 清空输入
      if (inputMode === 'text') {
        setVideoDescription('');
      }
    } catch (error: any) {
      console.error('创建任务时发生错误:', error);
      const errorMsg = error.response?.data?.detail || error.message || String(error);
      alert(`创建失败: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleTransform = (index: number) => {
    const newTransforms = [...transforms];
    newTransforms[index].enabled = !newTransforms[index].enabled;
    setTransforms(newTransforms);
  };

  const updateTransformParam = (index: number, key: string, value: any) => {
    const newTransforms = [...transforms];
    newTransforms[index].params[key] = value;
    setTransforms(newTransforms);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // 检查文件类型（放宽检查，支持常见视频格式）
      const videoExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'];
      const fileName = file.name.toLowerCase();
      const isVideo = file.type.startsWith('video/') || videoExtensions.some(ext => fileName.endsWith(ext));

      if (!isVideo) {
        alert('请选择视频文件（支持 mp4, mov, avi, mkv 等格式）');
        return;
      }
      setSelectedFile(file);
      console.log('文件已选择:', file.name, file.type, file.size);
      // 自动填充剧集名称（使用文件名）
      if (!dramaName) {
        const name = file.name.replace(/\.[^/.]+$/, ''); // 去掉扩展名
        setDramaName(name);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('请先选择视频文件');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      // 使用 FormData 直接上传到后端
      const formData = new FormData();
      formData.append('file', selectedFile);

      // 模拟上传进度
      setUploadProgress(30);

      const response = await apiClient.post('/fission/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        },
      });

      const { gcs_path } = response.data;

      // 设置GCS路径
      setSourceVideo(gcs_path);
      setUploadProgress(100);
      alert('视频上传成功！');
      setSelectedFile(null);
      loadGcsVideos();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      const errorMsg = error.response?.data?.detail || error.message || String(error);
      alert(`上传失败: ${errorMsg}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">🎞️ AI 裂变素材生成</h1>
          <p className="text-gray-500 mt-1">上传视频或输入文字描述，批量生成差异化变体素材</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-indigo-600">{totalJobs}</div>
            <div className="text-sm text-gray-500">总任务数</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-green-600">{jobs.filter((j) => j.status === "COMPLETED").length}</div>
            <div className="text-sm text-gray-500">已完成</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-blue-600">{jobs.filter((j) => j.status === "PROCESSING").length}</div>
            <div className="text-sm text-gray-500">处理中</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-purple-600">{gcsVideos.length}</div>
            <div className="text-sm text-gray-500">已上传视频</div>
          </div>
        </div>

        {/* 创建任务区域 */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🎬 创建裂变任务</h2>

          {/* 视频上传区域 */}
          <div className="mb-6">
            <h3 className="text-base font-medium mb-3">📹 上传视频</h3>
            <input ref={fileInputRef} type="file" accept="video/*" onChange={handleFileSelect} className="hidden" />
            <div
              onClick={() => !uploading && fileInputRef.current?.click()}
              className={`relative p-6 rounded-xl border-2 border-dashed transition-all cursor-pointer
                ${selectedFile
                  ? 'border-green-400 bg-green-50/50 hover:border-green-500'
                  : 'border-indigo-300 bg-indigo-50/30 hover:border-indigo-500 hover:bg-indigo-50/60'
                }
                ${uploading ? 'pointer-events-none opacity-70' : ''}
              `}
            >
              {!selectedFile ? (
                <div className="text-center">
                  <div className="text-5xl mb-3 opacity-60">🎬</div>
                  <p className="text-base font-medium text-gray-700">点击此处选择视频文件</p>
                  <p className="text-sm text-gray-400 mt-1">支持 MP4、MOV、AVI、MKV 等常见视频格式</p>
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-2xl">🎥</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{selectedFile.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                    className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors text-lg"
                    title="移除文件"
                  >✕</button>
                </div>
              )}
            </div>

            {/* 上传按钮 & 进度条 */}
            {selectedFile && (
              <div className="mt-3">
                <button onClick={handleUpload} disabled={!selectedFile || uploading}
                  className="w-full py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {uploading ? `上传中 ${uploadProgress}%` : '📤 上传视频'}
                </button>
              </div>
            )}
            {uploading && (
              <div className="mt-3">
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}
          </div>

          {/* 输入模式选择 */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">视频输入方式</label>
            <div className="flex gap-3">
              {([['upload', '📤 上传视频文件'], ['text', '✍️ 文字描述生成']] as const).map(([m, label]) => (
                <button key={m} onClick={() => setInputMode(m as 'upload' | 'text')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${inputMode === m ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* 根据输入模式显示不同的输入界面 */}
          {inputMode === 'upload' ? (
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-2">源视频路径</label>
                {gcsVideos.length > 0 && (
                  <select
                    value={sourceVideo}
                    onChange={(e) => setSourceVideo(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg mb-2"
                    disabled={uploading}
                  >
                    <option value="">-- 选择已有视频 --</option>
                    {gcsVideos.map((video, idx) => (
                      <option key={idx} value={video.gcs_path}>
                        {video.name}
                      </option>
                    ))}
                  </select>
                )}
                <input
                  type="text"
                  value={sourceVideo}
                  onChange={(e) => setSourceVideo(e.target.value)}
                  placeholder="gs://bucket/path/to/video.mp4 或上传视频自动填充"
                  className="w-full px-3 py-2 border rounded-lg"
                  readOnly={uploading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  💡 可以从下拉框选择已有视频、上传新视频，或手动输入GCS路径
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">剧集名称</label>
                <input
                  type="text"
                  value={dramaName}
                  onChange={(e) => setDramaName(e.target.value)}
                  placeholder="输入剧集名称"
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </div>
          ) : (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">视频描述</label>
              <textarea
                value={videoDescription}
                onChange={(e) => setVideoDescription(e.target.value)}
                placeholder="请描述您想要生成的视频内容，例如：一个阳光明媚的海滩场景，海浪轻轻拍打着沙滩，远处有几只海鸥在飞翔..."
                className="w-full px-3 py-2 border rounded-lg h-32 resize-none"
              />
              <p className="text-xs text-gray-500 mt-1">
                💡 详细描述视频场景、氛围、动作等，AI将根据描述生成视频
              </p>
              <div className="mt-3">
                <label className="block text-sm font-medium mb-2">剧集名称</label>
                <input
                  type="text"
                  value={dramaName}
                  onChange={(e) => setDramaName(e.target.value)}
                  placeholder="输入剧集名称"
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              生成变体数量: {variantCount}
            </label>
            <input
              type="range"
              min="5"
              max="20"
              value={variantCount}
              onChange={(e) => setVariantCount(parseInt(e.target.value))}
              className="w-full"
            />
          </div>

          {/* 变换配置 */}
          <div className="mb-4">
            <h3 className="text-base font-medium mb-3">🔧 变换配置</h3>
            <div className="space-y-3">
              {transforms.map((transform, index) => (
                <div key={index} className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl">
                  <input
                    type="checkbox"
                    checked={transform.enabled}
                    onChange={() => toggleTransform(index)}
                    className="w-5 h-5 accent-indigo-600"
                  />
                  <span className="font-medium min-w-[120px]">
                    {transform.type === 'filter' && '滤镜'}
                    {transform.type === 'duration_adjust' && '时长调整'}
                    {transform.type === 'frame_shuffle' && '抽帧重组'}
                    {transform.type === 'sticker_overlay' && '贴纸叠加'}
                  </span>
                  
                  {transform.enabled && transform.type === 'filter' && (
                    <select
                      value={transform.params.preset}
                      onChange={(e) => updateTransformParam(index, 'preset', e.target.value)}
                      className="px-3 py-1 border rounded"
                    >
                      <option value="warm">暖色调</option>
                      <option value="cool">冷色调</option>
                      <option value="vintage">复古</option>
                      <option value="high_contrast">高对比度</option>
                      <option value="soft">柔和</option>
                    </select>
                  )}
                  
                  {transform.enabled && transform.type === 'frame_shuffle' && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm">强度:</span>
                      <input
                        type="range"
                        min="0.1"
                        max="0.5"
                        step="0.1"
                        value={transform.params.intensity}
                        onChange={(e) => updateTransformParam(index, 'intensity', parseFloat(e.target.value))}
                        className="w-32"
                      />
                      <span className="text-sm">{transform.params.intensity}</span>
                    </div>
                  )}

                  {transform.enabled && transform.type === 'sticker_overlay' && (
                    <div className="flex flex-col gap-4 w-full">
                      {/* 贴纸操作按钮 */}
                      <div className="flex items-center gap-3 flex-wrap">
                        <button
                          onClick={() => {
                            const stickers = transform.params.stickers || [];
                            const newSticker: StickerData = {
                              id: `sticker-${Date.now()}`,
                              content: getStickerContent('tag_hot'),
                              x: 50,
                              y: 50,
                              size: 32,
                              rotation: 0,
                            };
                            updateTransformParam(index, 'stickers', [...stickers, newSticker]);
                          }}
                          className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 text-sm font-medium"
                        >
                          ➕ 文字贴纸
                        </button>

                        <button
                          onClick={() => {
                            setCurrentStickerTransformIndex(index);
                            setIsImageStickerPickerOpen(true);
                          }}
                          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium"
                        >
                          🖼️ 图片贴纸
                        </button>

                        <button
                          onClick={() => {
                            const stickers = transform.params.stickers || [];
                            const newSticker = generateRandomSticker();
                            updateTransformParam(index, 'stickers', [...stickers, newSticker]);
                          }}
                          className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 text-sm font-medium"
                        >
                          🎲 随机文字
                        </button>

                        <button
                          onClick={() => {
                            const stickers = transform.params.stickers || [];
                            const randomPath = getRandomStickerPath();
                            const newSticker: StickerData = {
                              id: `sticker-${Date.now()}`,
                              content: '',
                              x: Math.random() * 80 + 10,
                              y: Math.random() * 80 + 10,
                              size: [60, 80, 100, 120][Math.floor(Math.random() * 4)],
                              rotation: Math.floor(Math.random() * 360),
                              isImage: true,
                              imagePath: randomPath,
                            };
                            updateTransformParam(index, 'stickers', [...stickers, newSticker]);
                          }}
                          className="px-4 py-2 bg-gradient-to-r from-pink-500 to-orange-500 text-white rounded-lg hover:from-pink-600 hover:to-orange-600 text-sm font-medium"
                        >
                          🎨 随机图片
                        </button>

                        <button
                          onClick={() => {
                            const stickers = transform.params.stickers || [];
                            const randomStickers = Array.from({ length: 3 }, () => generateRandomSticker());
                            updateTransformParam(index, 'stickers', [...stickers, ...randomStickers]);
                          }}
                          className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 text-sm font-medium"
                        >
                          ✨ 随机3个
                        </button>

                        <button
                          onClick={() => {
                            updateTransformParam(index, 'stickers', []);
                          }}
                          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm font-medium"
                        >
                          🗑️ 清空全部
                        </button>

                        <span className="text-sm text-gray-600">
                          已添加 {(transform.params.stickers || []).length} 个贴纸
                        </span>
                      </div>

                      {/* 时间控制 */}
                      <div className="flex items-center gap-3 flex-wrap text-sm">
                        <div className="flex items-center gap-1">
                          <span className="text-gray-600">开始:</span>
                          <input
                            type="number"
                            min="0"
                            step="0.5"
                            value={transform.params.start_time || 0}
                            onChange={(e) => updateTransformParam(index, 'start_time', parseFloat(e.target.value) || 0)}
                            className="w-16 px-2 py-1 border rounded text-sm"
                          />
                          <span className="text-gray-500">秒</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-gray-600">结束:</span>
                          <input
                            type="number"
                            min="-1"
                            step="0.5"
                            value={transform.params.end_time ?? -1}
                            onChange={(e) => updateTransformParam(index, 'end_time', parseFloat(e.target.value))}
                            className="w-16 px-2 py-1 border rounded text-sm"
                          />
                          <span className="text-gray-500">秒 (-1=全程)</span>
                        </div>
                      </div>

                      {/* 可拖拽的多贴纸预览 */}
                      <div className="flex flex-col gap-2">
                        <span className="text-sm font-medium text-gray-700">
                          贴纸预览（9:16 竖屏，可拖拽调整位置，点击旋转按钮旋转）:
                        </span>
                        <div
                          className="relative mx-auto bg-gray-800 rounded-xl border-2 border-indigo-300 overflow-hidden"
                          style={{
                            width: '360px',
                            height: '640px',
                          }}
                          onClick={() => {
                            // 点击空白处取消选中
                          }}
                        >
                          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-xs">
                            9:16 竖屏视频预览 - 拖拽贴纸调整位置
                          </div>
                          <div className="absolute bottom-2 left-0 right-0 h-5 bg-gray-600/50 flex items-center justify-center">
                            <span className="text-[10px] text-gray-300">字幕区域（贴纸会避开）</span>
                          </div>

                          {/* 多贴纸编辑器 */}
                          <MultiStickerEditor
                            width={360}
                            height={640}
                            stickers={transform.params.stickers || []}
                            onStickersChange={(newStickers) => {
                              updateTransformParam(index, 'stickers', newStickers);
                            }}
                            enabled={true}
                          />
                        </div>
                        <p className="text-xs text-gray-500 text-center">
                          💡 拖拽贴纸调整位置 · 点击左上角蓝色按钮旋转 · 点击右上角红色按钮删除
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <button onClick={createJob} disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
          >
            {loading ? '创建中...' : '🚀 创建裂变任务'}
          </button>
        </div>

        {/* 任务列表 */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📋 任务列表</h2>
          
          <div className="space-y-4">
            {jobs.map((job) => {
              const isExpanded = expandedJobs.has(job.job_id);
              const detail = jobDetails[job.job_id];

              return (
                <div key={job.job_id} className="border rounded-xl p-5">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-semibold">{job.drama_name}</h3>
                      <p className="text-sm text-gray-500">
                        变体数量: {job.variant_count} | 创建者: {job.created_by}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          job.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                          job.status === 'PROCESSING' ? 'bg-blue-100 text-blue-800' :
                          job.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {job.status === 'COMPLETED' ? '✅ 已完成' :
                           job.status === 'PROCESSING' ? '⏳ 处理中' :
                           job.status === 'FAILED' ? '❌ 失败' :
                           '🕐 等待处理'}
                        </span>
                        <p className="text-sm text-gray-500 mt-1">{job.progress}%</p>
                      </div>
                      <button
                        onClick={() => toggleJobDetail(job.job_id)}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
                      >
                        {isExpanded ? '收起详情' : '查看详情'}
                      </button>
                    </div>
                  </div>

                  {/* 错误信息显示 */}
                  {job.status === 'FAILED' && job.error_message && (
                    <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                      ❌ {job.error_message}
                    </div>
                  )}

                  {job.status === 'PROCESSING' && (
                    <div className="mt-3">
                      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all"
                          style={{ width: `${job.progress}%` }} />
                      </div>
                    </div>
                  )}

                  {/* 展开的任务详情 */}
                  {isExpanded && detail && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="bg-gray-50 rounded-lg p-4 mb-4">
                        <h4 className="font-semibold mb-3">📄 任务详情</h4>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">任务ID：</span>
                            <span className="font-mono text-xs">{job.job_id}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">剧集名称：</span>
                            <span>{detail.drama_name}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">源视频：</span>
                            <span className="font-mono text-xs truncate block">{detail.source_video_path}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">创建时间：</span>
                            <span>{detail.created_at ? new Date(detail.created_at._seconds * 1000).toLocaleString('zh-CN') : '-'}</span>
                          </div>
                        </div>
                      </div>

                      {detail.variants && detail.variants.length > 0 && (
                        <>
                          <div className="flex justify-between items-center mb-3">
                            <h4 className="font-semibold">🎬 变体列表</h4>
                            <button
                              onClick={async () => {
                                if (!confirm(`确定要下载全部 ${detail.variants.length} 个变体吗？`)) {
                                  return;
                                }

                                let successCount = 0;
                                let failCount = 0;

                                for (let i = 0; i < detail.variants.length; i++) {
                                  const variant = detail.variants[i];
                                  try {
                                    const response = await apiClient.get(
                                      `/fission/jobs/${job.job_id}/download-url?variant_id=${variant.variant_id}`
                                    );

                                    const data = response.data;
                                    const a = document.createElement('a');
                                    a.href = data.download_url;
                                    a.download = `${detail.drama_name}_${variant.variant_id}.mp4`;
                                    a.style.display = 'none';
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    successCount++;
                                    await new Promise(resolve => setTimeout(resolve, 500));
                                  } catch (error) {
                                    failCount++;
                                    console.error(`下载 ${variant.variant_id} 失败:`, error);
                                  }
                                }

                                alert(`下载完成！成功: ${successCount}, 失败: ${failCount}`);
                              }}
                              className="px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                            >
                              📥 一键下载全部 ({detail.variants.length})
                            </button>
                          </div>

                          <div className="grid grid-cols-3 gap-4">
                            {detail.variants.map((variant: Variant) => (
                              <div key={variant.variant_id} className="border rounded-xl p-4 bg-white">
                                {variant.thumbnail_path && (
                                  <img src={variant.thumbnail_path} alt={variant.variant_id}
                                    className="w-full h-32 object-cover rounded-lg mb-2" />
                                )}
                                <p className="text-sm font-medium">{variant.variant_id}</p>
                                <p className="text-xs text-gray-500">时长: {variant.duration_seconds.toFixed(1)}s</p>
                                <p className="text-xs text-gray-500">大小: {(variant.file_size_bytes / 1024 / 1024).toFixed(1)}MB</p>
                                <div className="mt-2 flex gap-2">
                                  <button
                                    className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700"
                                    onClick={async () => {
                                      try {
                                        const response = await apiClient.get(
                                          `/fission/jobs/${job.job_id}/download-url?variant_id=${variant.variant_id}`
                                        );
                                        const a = document.createElement('a');
                                        a.href = response.data.download_url;
                                        a.download = `${detail.drama_name}_${variant.variant_id}.mp4`;
                                        a.style.display = 'none';
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                      } catch {
                                        alert('下载失败，请重试');
                                      }
                                    }}
                                  >
                                    📥 下载
                                  </button>
                                  <button
                                    className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-lg hover:bg-gray-200"
                                    onClick={async () => {
                                      try {
                                        const response = await apiClient.get(
                                          `/fission/jobs/${job.job_id}/download-url?variant_id=${variant.variant_id}`
                                        );
                                        window.open(response.data.download_url, '_blank');
                                      } catch {
                                        alert('预览失败，请重试');
                                      }
                                    }}
                                  >
                                    ▶ 预览
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 分页控件 */}
          <div className="mt-6 flex items-center justify-between border-t pt-4">
            <div className="text-sm text-gray-600">
              共 {totalJobs} 个任务，每页显示
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="mx-2 px-2 py-1 border rounded"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              条
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>

              <span className="text-sm text-gray-600">
                第 {currentPage} / {Math.ceil(totalJobs / pageSize) || 1} 页
              </span>

              <button
                onClick={() => setCurrentPage(Math.min(Math.ceil(totalJobs / pageSize), currentPage + 1))}
                disabled={currentPage >= Math.ceil(totalJobs / pageSize)}
                className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 图片贴纸选择器 */}
      <ImageStickerPicker
        isOpen={isImageStickerPickerOpen}
        onClose={() => setIsImageStickerPickerOpen(false)}
        onSelectSticker={(stickerPath) => {
          console.log('🎨 Selected sticker path:', stickerPath);
          if (currentStickerTransformIndex !== null) {
            const transform = transforms[currentStickerTransformIndex];
            const stickers = transform.params.stickers || [];
            const newSticker: StickerData = {
              id: `sticker-${Date.now()}`,
              content: '',
              x: 50,
              y: 50,
              size: 80,
              rotation: 0,
              isImage: true,
              imagePath: stickerPath,
            };
            console.log('🎨 Adding new sticker:', newSticker);
            updateTransformParam(currentStickerTransformIndex, 'stickers', [...stickers, newSticker]);
            console.log('🎨 Updated stickers:', [...stickers, newSticker]);
          }
        }}
      />
    </div>
  );
}

