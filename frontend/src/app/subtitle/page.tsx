"use client";

import { useState, useEffect, useCallback } from "react";
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
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [sourceLanguage, setSourceLanguage] = useState<string>("");
  const [targetLanguages, setTargetLanguages] = useState<string[]>([]);
  const [subtitleFormats, setSubtitleFormats] = useState<string[]>(["srt"]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

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

  // 文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(
        (f) => f.name.endsWith(".mp3") || f.name.endsWith(".wav") || f.name.endsWith(".mp4")
      );
      setSelectedFiles((prev) => [...prev, ...files]);
    }
  };

  // 拖拽处理
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files).filter(
      (f) => f.name.endsWith(".mp3") || f.name.endsWith(".wav") || f.name.endsWith(".mp4")
    );
    setSelectedFiles((prev) => [...prev, ...files]);
  };

  // 移除文件
  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
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

  // 开始处理
  const startProcessing = async () => {
    if (selectedFiles.length === 0 || targetLanguages.length === 0) {
      alert("请选择文件和目标语言");
      return;
    }

    setUploading(true);

    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("target_languages", JSON.stringify(targetLanguages));
      if (sourceLanguage) {
        formData.append("source_language", sourceLanguage);
      }

      try {
        await apiClient.post("/subtitle/upload", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
      } catch (error) {
        console.error("上传失败:", error);
      }
    }

    setSelectedFiles([]);
    setUploading(false);
    loadTasks();
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
            <div className="text-3xl font-bold text-purple-600">{languages.length}</div>
            <div className="text-sm text-gray-500">支持语言</div>
          </div>
        </div>

        {/* 文件上传区域 */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📁 文件上传</h2>
          <div
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
              dragOver ? "border-indigo-500 bg-indigo-50" : "border-indigo-300 bg-indigo-50/50"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("fileInput")?.click()}
          >
            <div className="text-5xl mb-4">📤</div>
            <div className="text-gray-600 mb-2">点击或拖拽文件到此处上传</div>
            <div className="text-sm text-gray-400">支持 MP3, WAV, MP4 格式</div>
            <input type="file" id="fileInput" className="hidden" accept=".mp3,.wav,.mp4" multiple onChange={handleFileSelect} />
          </div>

          {/* 已选文件列表 */}
          {selectedFiles.length > 0 && (
            <div className="mt-4 space-y-2">
              {selectedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🎵</span>
                    <div>
                      <div className="font-medium">{file.name}</div>
                      <div className="text-sm text-gray-500">{formatFileSize(file.size)}</div>
                    </div>
                  </div>
                  <button onClick={() => removeFile(index)} className="px-3 py-1 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600">
                    移除
                  </button>
                </div>
              ))}
            </div>
          )}
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
            disabled={selectedFiles.length === 0 || targetLanguages.length === 0 || uploading}
            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
          >
            {uploading ? "上传中..." : "🚀 开始处理"}
          </button>
          <button onClick={() => setSelectedFiles([])}
            className="px-8 py-3 bg-gray-100 text-gray-600 rounded-lg font-semibold hover:bg-gray-200"
          >
            🗑️ 清空文件
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
            <div className="space-y-4">
              {tasks.map((task) => {
                const isExpanded = expandedTask === task.task_id;
                return (
                <div key={task.task_id} className="border rounded-xl p-5">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-semibold">📄 {task.filename}</span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(task.status)}`}>
                          {getStatusText(task.status)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        目标语言: {task.target_languages.map(code => languages.find(l => l.code === code)?.name || code).join(", ")}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {task.status === "processing" && (
                        <span className="text-sm text-gray-500">{Math.round(task.progress * 100)}%</span>
                      )}
                      <button
                        onClick={() => setExpandedTask(isExpanded ? null : task.task_id)}
                        className={`px-4 py-2 rounded-lg text-sm ${isExpanded ? "bg-gray-200 text-gray-700" : "bg-indigo-600 text-white hover:bg-indigo-700"}`}
                      >
                        {isExpanded ? "收起详情" : "查看详情"}
                      </button>
                    </div>
                  </div>

                  {/* 进度条 */}
                  {(task.status === "processing" || task.status === "pending") && (
                    <div className="mt-3">
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all"
                          style={{ width: `${task.progress * 100}%` }} />
                      </div>
                    </div>
                  )}

                  {/* 错误信息 */}
                  {task.status === "failed" && task.error_message && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3 text-red-700 text-sm">
                      ❌ 错误: {task.error_message}
                    </div>
                  )}

                  {/* 展开详情面板 */}
                  {isExpanded && (
                    <div className="mt-4 border-t pt-4">
                      <h4 className="font-medium mb-3">📄 任务详情</h4>
                      <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                        <div className="bg-gray-50 rounded-lg p-3">
                          <span className="text-gray-500">任务ID</span>
                          <p className="font-mono text-xs mt-1">{task.task_id}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <span className="text-gray-500">文件名</span>
                          <p className="mt-1">{task.filename}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <span className="text-gray-500">源语言</span>
                          <p className="mt-1">{task.source_language ? (languages.find(l => l.code === task.source_language)?.name || task.source_language) : "自动识别"}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <span className="text-gray-500">创建时间</span>
                          <p className="mt-1">{new Date(task.created_at).toLocaleString("zh-CN")}</p>
                        </div>
                      </div>

                      {/* 字幕文件下载列表 */}
                      {task.status === "completed" && task.subtitle_files && task.subtitle_files.length > 0 && (
                        <div>
                          <div className="flex justify-between items-center mb-3">
                            <h4 className="font-medium">📥 字幕文件</h4>
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
                              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                            >
                              📥 一键下载全部 ({task.subtitle_files.length})
                            </button>
                          </div>
                          <div className="grid grid-cols-3 gap-3">
                            {task.subtitle_files.map((file, idx) => (
                              <div key={idx} className="border rounded-xl p-4">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-2xl">📝</span>
                                  <div>
                                    <p className="text-sm font-medium">{languages.find(l => l.code === file.language)?.name || file.language}</p>
                                    <p className="text-xs text-gray-500">{file.format.toUpperCase()} · {formatFileSize(file.file_size)}</p>
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  <button
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
                                      } catch { alert("下载失败，请重试"); }
                                    }}
                                    className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700"
                                  >
                                    📥 下载
                                  </button>
                                  <button
                                    onClick={async () => {
                                      try {
                                        const res = await apiClient.get(`/subtitle/download/${task.task_id}/${file.language}/${file.format}`);
                                        if (res.data.download_url) window.open(res.data.download_url, "_blank");
                                      } catch { alert("预览失败，请重试"); }
                                    }}
                                    className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-lg hover:bg-gray-200"
                                  >
                                    👁 预览
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="text-sm text-gray-400 mt-3 pt-3 border-t">
                    ⏰ 创建时间: {new Date(task.created_at).toLocaleString("zh-CN")}
                    {task.completed_at && ` | ✅ 完成时间: ${new Date(task.completed_at).toLocaleString("zh-CN")}`}
                  </div>
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
