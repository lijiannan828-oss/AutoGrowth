"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuthContext } from "@/context/AuthContext";
import apiClient from "@/lib/api-client";

interface Voice {
  voice_id: string;
  name: string;
  language: string;
  gender: string;
}

interface TTSTask {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  text: string;
  voice_id: string;
  audio_file?: string;
  filename?: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

const LANGUAGES = [
  { code: "zh", name: "简体中文" },
  { code: "zh-TW", name: "繁体中文" },
  { code: "en", name: "English" },
  { code: "ja", name: "日本語" },
  { code: "ko", name: "한국어" },
  { code: "es", name: "Español" },
  { code: "id", name: "Bahasa Indonesia" },
  { code: "th", name: "ภาษาไทย" },
  { code: "vi", name: "Tiếng Việt" },
  { code: "fr", name: "Français" },
];

export default function TTSPage() {
  const { user } = useAuthContext();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [tasks, setTasks] = useState<TTSTask[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState("zh");
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [rate, setRate] = useState(1.0);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  // 加载音色列表
  useEffect(() => {
    apiClient.get(`/tts/voices?language=${selectedLanguage}`)
      .then((res) => {
        setVoices(res.data.voices || []);
        if (res.data.voices?.length > 0) {
          setSelectedVoice(res.data.voices[0].voice_id);
        }
      })
      .catch(console.error);
  }, [selectedLanguage]);

  // 加载任务列表
  const loadTasks = useCallback(async () => {
    try {
      const res = await apiClient.get("/tts/tasks");
      setTasks(res.data.tasks || []);
    } catch (error) {
      console.error("加载任务失败:", error);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 2000);
    return () => clearInterval(interval);
  }, [loadTasks]);

  // 文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter((f) => f.name.endsWith(".txt"));
      setSelectedFiles((prev) => [...prev, ...files]);
    }
  };

  // 拖拽处理
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith(".txt"));
    setSelectedFiles((prev) => [...prev, ...files]);
  };

  // 移除文件
  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // 开始处理
  const startProcessing = async () => {
    if (selectedFiles.length === 0 || !selectedVoice) {
      alert("请选择文件和音色");
      return;
    }

    setUploading(true);

    for (const file of selectedFiles) {
      try {
        const text = await file.text();
        if (!text.trim()) continue;

        const formData = new FormData();
        formData.append("text", text.trim());
        formData.append("voice_id", selectedVoice);
        formData.append("rate", rate.toString());
        formData.append("filename", file.name.replace(".txt", ""));

        await apiClient.post("/tts/convert", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } catch (error) {
        console.error("转换失败:", error);
      }
    }

    setSelectedFiles([]);
    setUploading(false);
    loadTasks();
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
          <h1 className="text-3xl font-bold text-gray-900">🔊 AI 文字转语音</h1>
          <p className="text-gray-500 mt-1">支持多语言、多音色的文字转语音服务</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-indigo-600">{tasks.length}</div>
            <div className="text-sm text-gray-500">总任务数</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-green-600">
              {tasks.filter((t) => t.status === "completed").length}
            </div>
            <div className="text-sm text-gray-500">已完成</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-blue-600">
              {tasks.filter((t) => t.status === "processing").length}
            </div>
            <div className="text-sm text-gray-500">处理中</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-purple-600">
              {tasks.filter((t) => t.status === "completed" && t.audio_file).length}
            </div>
            <div className="text-sm text-gray-500">已上传</div>
          </div>
        </div>

        {/* 文件上传区域 */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📁 上传文本文件</h2>
            <div
              className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
                dragOver ? "border-indigo-500 bg-indigo-50" : "border-indigo-300 bg-indigo-50/50"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById("ttsFileInput")?.click()}
            >
              <div className="text-5xl mb-4">📤</div>
              <div className="text-gray-600 mb-2">点击或拖拽 TXT 文件到此处上传</div>
              <div className="text-sm text-gray-400">支持 TXT 格式，最多10个文件</div>
              <input
                type="file"
                id="ttsFileInput"
                className="hidden"
                accept=".txt"
                multiple
                onChange={handleFileSelect}
              />
            </div>

            {/* 已选文件列表 */}
            {selectedFiles.length > 0 && (
              <div className="mt-4 space-y-2">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">📄</span>
                      <div className="font-medium">{file.name}</div>
                    </div>
                    <button
                      onClick={() => removeFile(index)}
                      className="px-3 py-1 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600"
                    >
                      移除
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 配置选项 */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🎤 音色配置</h2>

            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* 语言选择 */}
              <div>
                <label className="block text-sm font-medium mb-2">选择语言</label>
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className="w-full p-3 border rounded-lg"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
              </div>

              {/* 语速调节 */}
              <div>
                <label className="block text-sm font-medium mb-2">语速: {rate.toFixed(1)}x</label>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-500">慢</span>
                  <input
                    type="range"
                    min="0.8"
                    max="1.5"
                    step="0.1"
                    value={rate}
                    onChange={(e) => setRate(parseFloat(e.target.value))}
                    className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-sm text-gray-500">快</span>
                </div>
              </div>
            </div>

            {/* 音色选择 */}
            <div>
              <label className="block text-sm font-medium mb-2">选择音色</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {voices.map((voice) => (
                  <div
                    key={voice.voice_id}
                    onClick={() => setSelectedVoice(voice.voice_id)}
                    className={`p-4 border rounded-xl cursor-pointer transition-all text-center ${
                      selectedVoice === voice.voice_id
                        ? "border-indigo-500 bg-indigo-50 shadow-md"
                        : "border-gray-200 hover:border-indigo-300"
                    }`}
                  >
                    <div className="font-medium">{voice.name}</div>
                    <div className="text-sm text-gray-500">
                      {voice.gender === "male" ? "👨 男声" : "👩 女声"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-4 mb-8">
            <button
              onClick={startProcessing}
              disabled={selectedFiles.length === 0 || !selectedVoice || uploading}
              className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
            >
              {uploading ? "处理中..." : "🚀 开始转换"}
            </button>
            <button
              onClick={() => setSelectedFiles([])}
              className="px-8 py-3 bg-gray-100 text-gray-600 rounded-lg font-semibold hover:bg-gray-200"
            >
              🗑️ 清空文件
            </button>
          </div>

          {/* 任务列表 */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📋 转换任务</h2>
            {tasks.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <div className="text-6xl mb-4 opacity-50">🔊</div>
                <h3 className="text-lg font-medium">暂无转换任务</h3>
                <p>上传文本文件开始语音合成</p>
              </div>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => {
                  const isExpanded = expandedTask === task.task_id;
                  return (
                  <div key={task.task_id} className="border rounded-xl p-5">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-semibold">🔊 {task.filename || task.text}</h3>
                        <p className="text-sm text-gray-500 mt-1">
                          音色: {task.voice_id} | 创建时间: {new Date(task.created_at).toLocaleString("zh-CN")}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(task.status)}`}>
                            {task.status === 'completed' ? '✅ 已完成' :
                             task.status === 'processing' ? '⏳ 处理中' :
                             task.status === 'failed' ? '❌ 失败' :
                             '🕐 等待处理'}
                          </span>
                          <p className="text-sm text-gray-500 mt-1">{task.progress}%</p>
                        </div>
                        <button
                          onClick={() => setExpandedTask(isExpanded ? null : task.task_id)}
                          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
                        >
                          {isExpanded ? "收起详情" : "查看详情"}
                        </button>
                      </div>
                    </div>

                    {/* 错误信息显示 */}
                    {task.status === 'failed' && task.error_message && (
                      <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                        ❌ {task.error_message}
                      </div>
                    )}

                    {/* 进度条 */}
                    {task.status === 'processing' && (
                      <div className="mt-3">
                        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                          <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all"
                            style={{ width: `${task.progress}%` }} />
                        </div>
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
                            <span className="text-gray-500">音色</span>
                            <p className="mt-1">{task.voice_id}</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <span className="text-gray-500">文本预览</span>
                            <p className="mt-1 line-clamp-2">{task.text}</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <span className="text-gray-500">创建时间</span>
                            <p className="mt-1">{new Date(task.created_at).toLocaleString("zh-CN")}</p>
                          </div>
                        </div>

                        {/* 音频操作 */}
                        {task.status === "completed" && task.audio_file && (
                          <div>
                            <div className="flex justify-between items-center mb-3">
                              <h4 className="font-medium">🎧 音频操作</h4>
                            </div>
                            <div className="grid grid-cols-3 gap-3">
                              <div className="border rounded-xl p-4">
                                <p className="text-sm font-medium mb-2">🔊 生成的音频</p>
                                <div className="flex gap-2">
                                  <button
                                    onClick={async () => {
                                      try {
                                        const res = await apiClient.get(`/tts/download/${task.audio_file}`);
                                        if (res.data.download_url) {
                                          const audio = new Audio(res.data.download_url);
                                          audio.play().catch(() => alert("播放失败"));
                                        }
                                      } catch (_e) { alert("获取播放链接失败"); }
                                    }}
                                    className="text-xs bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700"
                                  >
                                    ▶ 播放
                                  </button>
                                  <button
                                    onClick={async () => {
                                      try {
                                        const res = await apiClient.get(`/tts/download/${task.audio_file}`);
                                        if (res.data.download_url) {
                                          const a = document.createElement('a');
                                          a.href = res.data.download_url;
                                          a.download = `${task.filename || task.task_id}.mp3`;
                                          a.style.display = 'none';
                                          document.body.appendChild(a);
                                          a.click();
                                          document.body.removeChild(a);
                                        }
                                      } catch (_e) { alert("下载失败，请重试"); }
                                    }}
                                    className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700"
                                  >
                                    📥 下载
                                  </button>
                                  <button
                                    onClick={async () => {
                                      try {
                                        const res = await apiClient.get(`/tts/download/${task.audio_file}`);
                                        if (res.data.download_url) window.open(res.data.download_url, "_blank");
                                      } catch (_e) { alert("预览失败，请重试"); }
                                    }}
                                    className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-lg hover:bg-gray-200"
                                  >
                                    👁 预览
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
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

