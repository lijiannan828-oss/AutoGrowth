"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuthContext } from "@/context/AuthContext";
import apiClient from "@/lib/api-client";

interface Language {
  code: string;
  name: string;
}

interface SubtitleFile {
  language: string;
  format: string;
  file_path: string;
  file_size: number;
}

interface SubtitleTask {
  task_id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  source_language: string | null;
  target_languages: string[];
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  subtitle_files: SubtitleFile[] | null;
}

export default function SubtitlePage() {
  const { user } = useAuthContext();
  const [languages, setLanguages] = useState<Language[]>([]);
  const [tasks, setTasks] = useState<SubtitleTask[]>([]);
  const [sourceLanguage, setSourceLanguage] = useState<string>("");
  const [targetLanguages, setTargetLanguages] = useState<string[]>([]);
  const [subtitleFormats, setSubtitleFormats] = useState<string[]>(["srt"]);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  // 文件上传相关状态（参考裂变模块）
  const [sourceMode, setSourceMode] = useState<'select' | 'upload' | 'manual'>('select');
  const [sourceVideo, setSourceVideo] = useState('');
  const [gcsVideos, setGcsVideos] = useState<any[]>([]);
  const [videoSearch, setVideoSearch] = useState('');
  const [videoSortBy, setVideoSortBy] = useState<'name' | 'time'>('name');
  const [videoDropdownOpen, setVideoDropdownOpen] = useState(false);
  const [renamingVideoId, setRenamingVideoId] = useState<string | null>(null);
  const [newDisplayName, setNewDisplayName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [videoDisplayName, setVideoDisplayName] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoDropdownRef = useRef<HTMLDivElement>(null);

  // 加载语言列表
  useEffect(() => {
    apiClient.get("/subtitle/languages")
      .then((res) => setLanguages(res.data.languages || []))
      .catch(console.error);
  }, []);

  // 加载任务列表
  const loadTasks = useCallback(async () => {
    try {
      const res = await apiClient.get("/subtitle/tasks");
      setTasks(res.data.tasks || []);
    } catch (error) {
      console.error("加载任务失败:", error);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 3000);
    return () => clearInterval(interval);
  }, [loadTasks]);

  // 加载已上传视频列表
  const loadGcsVideos = useCallback(async () => {
    try {
      const res = await apiClient.get("/subtitle/videos");
      setGcsVideos(res.data.videos || []);
    } catch (error) {
      console.error("加载视频列表失败:", error);
    }
  }, []);

  useEffect(() => {
    loadGcsVideos();
  }, [loadGcsVideos]);

  // 点击外部关闭下拉
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (videoDropdownRef.current && !videoDropdownRef.current.contains(e.target as Node)) {
        setVideoDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 文件选择（单文件）
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setVideoDisplayName(file.name.replace(/\.[^/.]+$/, ""));
    }
  };

  // 上传视频到 GCS
  const handleUpload = async () => {
    if (!selectedFile) return;

    // 检查重复文件
    const existing = gcsVideos.find(v => v.original_filename === selectedFile.name);
    if (existing) {
      setSourceMode('select');
      setSourceVideo(existing.gcs_path);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    try {
      const res = await apiClient.post("/subtitle/upload", (() => {
        const fd = new FormData();
        fd.append("file", selectedFile);
        if (videoDisplayName.trim()) fd.append("display_name", videoDisplayName.trim());
        return fd;
      })(), {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000,
        onUploadProgress: (e: any) => {
          const pct = Math.round((e.loaded * 90) / (e.total || 1));
          setUploadProgress(Math.min(pct, 90));
        },
      });
      const { gcs_path } = res.data;
      setSourceVideo(gcs_path);
      setUploadProgress(100);
      setSelectedFile(null);
      setVideoDisplayName('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadGcsVideos();
      setSourceMode('select');
    } catch (error) {
      console.error("上传失败:", error);
      alert("上传失败，请重试");
    } finally {
      setUploading(false);
    }
  };

  // 重命名视频
  const handleRename = async (videoId: string) => {
    if (!newDisplayName.trim()) return;
    try {
      await apiClient.patch(`/subtitle/videos/${videoId}`, { display_name: newDisplayName.trim() });
      setRenamingVideoId(null);
      setNewDisplayName('');
      await loadGcsVideos();
    } catch (error) {
      console.error("重命名失败:", error);
      alert("重命名失败");
    }
  };

  // 切换目标语言
  const toggleTargetLanguage = (code: string) => {
    setTargetLanguages((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  // 切换字幕格式
  const toggleFormat = (format: string) => {
    setSubtitleFormats((prev) =>
      prev.includes(format) ? prev.filter((f) => f !== format) : [...prev, format]
    );
  };

  // 开始处理（从已选视频创建字幕任务）
  const startProcessing = async () => {
    if (!sourceVideo || targetLanguages.length === 0) {
      alert("请选择视频和目标语言");
      return;
    }

    setUploading(true);
    try {
      await apiClient.post("/subtitle/tasks", {
        source_video_path: sourceVideo,
        target_languages: targetLanguages,
        ...(sourceLanguage ? { source_language: sourceLanguage } : {}),
      });
      loadTasks();
    } catch (error) {
      console.error("创建任务失败:", error);
      alert("创建任务失败，请重试");
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  };

  const getStatusText = (status: string) => {
    const map: Record<string, string> = {
      pending: "等待中",
      processing: "处理中",
      completed: "已完成",
      failed: "失败",
    };
    return map[status] || status;
  };

  const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-800",
      processing: "bg-blue-100 text-blue-800",
      completed: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
    };
    return map[status] || "bg-gray-100 text-gray-800";
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>请先登录</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">🎬 AI 多语言字幕生成</h1>
          <p className="text-gray-500 mt-1">支持音频/视频文件，自动识别语音并生成多语言字幕</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-indigo-600">{tasks.length}</div>
            <div className="text-sm text-gray-500">总任务数</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-green-600">{tasks.filter((t) => t.status === "completed").length}</div>
            <div className="text-sm text-gray-500">已完成</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-blue-600">{tasks.filter((t) => t.status === "processing").length}</div>
            <div className="text-sm text-gray-500">处理中</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-purple-600">
              {tasks.filter((t) => t.status === "completed" && t.subtitle_files).reduce((sum, t) => sum + (t.subtitle_files?.length || 0), 0)}
            </div>
            <div className="text-sm text-gray-500">已上传</div>
          </div>
        </div>

        {/* 文件上传区域 */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📁 文件上传</h2>
          <div>
            <label className="block text-sm font-medium mb-2">源视频路径</label>
            {/* 三选项卡 */}
            <div className="flex gap-1 mb-3">
              {([['select', '📂 选择已有视频'], ['upload', '📤 上传新视频'], ['manual', '✏️ 手动输入路径']] as const).map(([m, label]) => (
                <button key={m} onClick={() => setSourceMode(m as 'select' | 'upload' | 'manual')}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${sourceMode === m ? "bg-indigo-100 text-indigo-700 border border-indigo-300" : "bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100"}`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* 选择已有视频 */}
            {sourceMode === 'select' && (
              <div>
                <div ref={videoDropdownRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setVideoDropdownOpen(!videoDropdownOpen)}
                    className="w-full px-3 py-2 border rounded-lg bg-white text-left flex items-center justify-between"
                  >
                    <span className={sourceVideo ? 'text-gray-900 truncate' : 'text-gray-400'}>
                      {sourceVideo
                        ? (gcsVideos.find(v => v.gcs_path === sourceVideo)?.display_name
                          || gcsVideos.find(v => v.gcs_path === sourceVideo)?.name
                          || sourceVideo)
                        : '-- 选择已有视频 --'}
                    </span>
                    <span className="text-gray-400 ml-2 flex-shrink-0">{videoDropdownOpen ? '▲' : '▼'}</span>
                  </button>

                  {videoDropdownOpen && (
                    <div className="absolute z-50 mt-1 w-full bg-white border rounded-lg shadow-lg max-h-80 flex flex-col">
                      <div className="p-2 border-b flex gap-2 items-center">
                        <input
                          type="text"
                          value={videoSearch}
                          onChange={(e) => setVideoSearch(e.target.value)}
                          placeholder="搜索视频名称..."
                          className="flex-1 px-2 py-1.5 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); setVideoSortBy(videoSortBy === 'name' ? 'time' : 'name'); }}
                          className={`px-2 py-1.5 rounded text-xs font-medium whitespace-nowrap border transition-colors ${videoSortBy === 'name' ? 'bg-indigo-50 text-indigo-700 border-indigo-300' : 'bg-amber-50 text-amber-700 border-amber-300'}`}
                        >
                          {videoSortBy === 'name' ? '🔤 名称' : '🕐 时间'}
                        </button>
                      </div>
                      <div className="overflow-y-auto flex-1">
                        {(() => {
                          const filtered = gcsVideos.filter(v => {
                            if (!videoSearch.trim()) return true;
                            const keyword = videoSearch.trim().toLowerCase();
                            const name = (v.display_name || v.name || '').toLowerCase();
                            const original = (v.original_filename || '').toLowerCase();
                            return name.includes(keyword) || original.includes(keyword);
                          });
                          const sorted = [...filtered].sort((a, b) => {
                            if (videoSortBy === 'time') {
                              const ta = a.updated || '';
                              const tb = b.updated || '';
                              return tb.localeCompare(ta);
                            }
                            const na = (a.display_name || a.name || '').toLowerCase();
                            const nb = (b.display_name || b.name || '').toLowerCase();
                            return na.localeCompare(nb, 'zh-CN');
                          });
                          if (sorted.length === 0) {
                            return <div className="px-3 py-4 text-sm text-gray-400 text-center">无匹配视频</div>;
                          }
                          return sorted.map((video, idx) => (
                            <button
                              key={video.video_id || idx}
                              type="button"
                              onClick={() => { setSourceVideo(video.gcs_path); setVideoDropdownOpen(false); setVideoSearch(''); }}
                              className={`w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 transition-colors ${sourceVideo === video.gcs_path ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-700'}`}
                            >
                              {video.display_name || video.name}
                              {video.display_name && video.original_filename && (
                                <span className="text-gray-400 ml-1">({video.original_filename})</span>
                              )}
                            </button>
                          ));
                        })()}
                      </div>
                    </div>
                  )}
                </div>
                {sourceVideo && (
                  <div className="mt-2">
                    {renamingVideoId ? (
                      <div className="flex items-center gap-2">
                        <input type="text" value={newDisplayName} onChange={(e) => setNewDisplayName(e.target.value)}
                          className="flex-1 px-2 py-1 border rounded text-xs" maxLength={100} autoFocus />
                        <button onClick={() => handleRename(renamingVideoId)}
                          className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 whitespace-nowrap">确认</button>
                        <button onClick={() => { setRenamingVideoId(null); setNewDisplayName(''); }}
                          className="px-2 py-1 text-gray-500 hover:text-gray-700 text-xs whitespace-nowrap">取消</button>
                      </div>
                    ) : (
                      <button onClick={() => {
                        const video = gcsVideos.find(v => v.gcs_path === sourceVideo);
                        if (video && video.video_id) { setRenamingVideoId(video.video_id); setNewDisplayName(video.display_name || video.name); }
                      }} className="text-xs text-blue-600 hover:text-blue-800">✏️ 重命名此视频</button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 上传新视频 */}
            {sourceMode === 'upload' && (
              <div>
                <input ref={fileInputRef} type="file" accept=".mp4,.mov,.avi,.mkv,.mp3,.wav,.webm,.flv" onChange={handleFileSelect} className="hidden" />
                <div
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  className={`relative p-4 rounded-lg border-2 border-dashed transition-all cursor-pointer
                    ${selectedFile ? 'border-green-400 bg-green-50/50 hover:border-green-500' : 'border-indigo-300 bg-indigo-50/30 hover:border-indigo-500 hover:bg-indigo-50/60'}
                    ${uploading ? 'pointer-events-none opacity-70' : ''}`}
                >
                  {!selectedFile ? (
                    <div className="text-center py-2">
                      <div className="text-3xl mb-2 opacity-60">🎬</div>
                      <p className="text-sm font-medium text-gray-700">点击选择视频/音频文件</p>
                      <p className="text-xs text-gray-400 mt-1">支持 MP4、MOV、AVI、MKV、MP3、WAV</p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center text-xl">🎥</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{selectedFile.name}</p>
                        <p className="text-xs text-gray-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                        className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors" title="移除文件">✕</button>
                    </div>
                  )}
                </div>
                {selectedFile && (
                  <div className="mt-3">
                    <label className="block text-xs font-medium text-gray-700 mb-1">视频显示名称</label>
                    <input type="text" value={videoDisplayName} onChange={(e) => setVideoDisplayName(e.target.value)}
                      placeholder="输入视频名称（可选）" className="w-full px-3 py-1.5 border rounded-lg text-sm" maxLength={100} />
                    <button onClick={handleUpload} disabled={!selectedFile || uploading}
                      className="w-full mt-2 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                      {uploading ? `上传中 ${uploadProgress}%` : '📤 上传视频'}
                    </button>
                  </div>
                )}
                {uploading && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-1.5 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 手动输入GCS路径 */}
            {sourceMode === 'manual' && (
              <div>
                <input type="text" value={sourceVideo} onChange={(e) => setSourceVideo(e.target.value)}
                  placeholder="gs://bucket/path/to/video.mp4" className="w-full px-3 py-2 border rounded-lg" />
                <p className="text-xs text-gray-400 mt-1">直接输入 GCS 视频路径</p>
              </div>
            )}

            {/* 当前已选路径 */}
            {sourceVideo && sourceMode !== 'manual' && (
              <p className="text-xs text-gray-500 mt-2 truncate" title={sourceVideo}>已选: {sourceVideo}</p>
            )}
          </div>
        </div>

        {/* 配置选项 */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">⚙️ 配置选项</h2>

          {/* 源语言 */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">源语言（留空自动识别）</label>
            <select value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)}
              className="w-full max-w-xs p-2 border rounded-lg">
              <option value="">🔍 自动识别</option>
              {languages.map((lang) => (
                <option key={lang.code} value={lang.code}>{lang.name}</option>
              ))}
            </select>
          </div>

          {/* 目标语言 */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">目标翻译语言（至少选择一个）</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
              {languages.map((lang) => (
                <label key={lang.code}
                  className={`flex items-center p-2 border rounded-lg cursor-pointer transition-all ${
                    targetLanguages.includes(lang.code) ? "border-purple-600 bg-purple-50" : "border-gray-200 hover:border-purple-300"
                  }`}
                >
                  <input type="checkbox" checked={targetLanguages.includes(lang.code)} onChange={() => toggleTargetLanguage(lang.code)} className="mr-2" />
                  <span className="text-sm">{lang.name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* 字幕格式 */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">字幕格式</label>
            <div className="flex gap-4">
              <label className={`flex-1 p-4 border rounded-lg cursor-pointer transition-all ${
                subtitleFormats.includes("srt") ? "border-indigo-500 bg-indigo-50" : "border-gray-200"
              }`}>
                <input type="checkbox" checked={subtitleFormats.includes("srt")} onChange={() => toggleFormat("srt")} className="mr-2" />
                <span className="font-medium">SRT 格式</span>
                <p className="text-sm text-gray-400 mt-1">纯文本时间轴格式，通用性强</p>
              </label>
              <label className={`flex-1 p-4 border rounded-lg cursor-pointer transition-all ${
                subtitleFormats.includes("ass") ? "border-indigo-500 bg-indigo-50" : "border-gray-200"
              }`}>
                <input type="checkbox" checked={subtitleFormats.includes("ass")} onChange={() => toggleFormat("ass")} className="mr-2" />
                <span className="font-medium">ASS 格式</span>
                <p className="text-sm text-gray-400 mt-1">支持高级样式，适合短剧</p>
              </label>
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-4 mb-6">
          <button onClick={startProcessing}
            disabled={!sourceVideo || targetLanguages.length === 0 || uploading}
            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
          >
            {uploading ? "处理中..." : "🚀 开始处理"}
          </button>
        </div>

        {/* 任务列表 */}
        <div>
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📋 处理任务</h2>
          {tasks.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-6xl mb-4 opacity-50">📋</div>
              <h3 className="text-lg font-medium">暂无处理任务</h3>
              <p>上传文件开始生成字幕</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => {
                const isExpanded = expandedTask === task.task_id;
                return (
                <div key={task.task_id} className="border rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold truncate">📄 {task.filename}</span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium flex-shrink-0 ${getStatusColor(task.status)}`}>
                          {getStatusText(task.status)} {Math.round(task.progress)}%
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 truncate">
                        {task.target_languages.map(code => languages.find(l => l.code === code)?.name || code).join(", ")}
                      </p>
                    </div>
                    <button
                      onClick={() => setExpandedTask(isExpanded ? null : task.task_id)}
                      className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 flex-shrink-0"
                    >
                      {isExpanded ? "收起" : "详情"}
                    </button>
                  </div>

                  {/* 错误信息显示 */}
                  {task.status === "failed" && task.error_message && (
                    <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                      ❌ {task.error_message}
                    </div>
                  )}

                  {/* 进度条 */}
                  {task.status === "processing" && (
                    <div className="mt-3">
                      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all"
                          style={{ width: `${task.progress}%` }} />
                      </div>
                    </div>
                  )}

                  {/* 展开详情面板 */}
                  {isExpanded && (
                    <div className="mt-2 border-t pt-2">
                      <div className="grid grid-cols-4 gap-2 text-sm mb-2">
                        <div className="bg-gray-50 rounded px-2 py-1.5">
                          <span className="text-gray-400">ID</span>
                          <p className="font-mono truncate">{task.task_id}</p>
                        </div>
                        <div className="bg-gray-50 rounded px-2 py-1.5">
                          <span className="text-gray-400">文件</span>
                          <p className="truncate">{task.filename}</p>
                        </div>
                        <div className="bg-gray-50 rounded px-2 py-1.5">
                          <span className="text-gray-400">源语言</span>
                          <p>{task.source_language ? (languages.find(l => l.code === task.source_language)?.name || task.source_language) : "自动识别"}</p>
                        </div>
                        <div className="bg-gray-50 rounded px-2 py-1.5">
                          <span className="text-gray-400">创建</span>
                          <p>{new Date(task.created_at).toLocaleString("zh-CN")}</p>
                        </div>
                      </div>

                      {/* 字幕文件下载列表 */}
                      {task.status === "completed" && task.subtitle_files && task.subtitle_files.length > 0 && (
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-sm font-medium text-gray-500">📥 字幕文件</span>
                            <button
                              onClick={async () => {
                                if (!task.subtitle_files) return;
                                let success = 0, fail = 0;
                                for (const file of task.subtitle_files) {
                                  try {
                                    const res = await apiClient.get(`/subtitle/download/${task.task_id}/${file.language}/${file.format}`);
                                    if (res.data.download_url) {
                                      const a = document.createElement("a");
                                      a.href = res.data.download_url;
                                      a.download = `${task.filename}_${file.language}.${file.format}`;
                                      a.style.display = "none";
                                      document.body.appendChild(a);
                                      a.click();
                                      document.body.removeChild(a);
                                      success++;
                                      await new Promise(r => setTimeout(r, 500));
                                    }
                                  } catch { fail++; }
                                }
                                alert(`下载完成！成功: ${success}, 失败: ${fail}`);
                              }}
                              className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                            >
                              全部下载 ({task.subtitle_files.length})
                            </button>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {task.subtitle_files.map((file, idx) => (
                              <button
                                key={idx}
                                onClick={async () => {
                                  try {
                                    const res = await apiClient.get(`/subtitle/download/${task.task_id}/${file.language}/${file.format}`);
                                    if (res.data.download_url) {
                                      const a = document.createElement("a");
                                      a.href = res.data.download_url;
                                      a.download = `${task.filename}_${file.language}.${file.format}`;
                                      a.style.display = "none";
                                      document.body.appendChild(a);
                                      a.click();
                                      document.body.removeChild(a);
                                    }
                                  } catch { alert("下载失败"); }
                                }}
                                className="inline-flex items-center gap-1 px-2 py-1 border rounded text-sm hover:bg-indigo-50 hover:border-indigo-300 transition-colors"
                              >
                                <span>{languages.find(l => l.code === file.language)?.name || file.language}</span>
                                <span className="text-gray-400">.{file.format}</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {!isExpanded && (
                    <div className="text-sm text-gray-400 mt-1">
                      {new Date(task.created_at).toLocaleString("zh-CN")}
                      {task.completed_at && ` → ${new Date(task.completed_at).toLocaleString("zh-CN")}`}
                    </div>
                  )}
                </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
