"use client";

import { useState, useRef, useEffect } from "react";
import apiClient from "@/lib/api-client";

/* ---------- 类型 ---------- */

interface TTSTask {
  task_id: string;
  status: string;
  progress: number;
  audio_file?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  text?: string;
  voice_id?: string;
}

interface Voice {
  voice_id: string;
  name: string;
  language: string;
  gender: string;
}

/* ---------- 常量 ---------- */

const LANGUAGE_OPTIONS = [
  { value: "zh", label: "🇨🇳 简体中文" },
  { value: "zh-TW", label: "🇹🇼 繁体中文" },
  { value: "en", label: "🇺🇸 英语" },
  { value: "ja", label: "🇯🇵 日语" },
  { value: "ko", label: "🇰🇷 韩语" },
  { value: "es", label: "🇪🇸 西班牙语" },
  { value: "id", label: "🇮🇩 印尼语" },
  { value: "ar", label: "🇸🇦 阿拉伯语" },
  { value: "th", label: "🇹🇭 泰语" },
  { value: "vi", label: "🇻🇳 越南语" },
  { value: "fr", label: "🇫🇷 法语" },
];

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending:    { label: "等待中", color: "bg-yellow-100 text-yellow-800" },
  processing: { label: "生成中", color: "bg-blue-100 text-blue-800" },
  completed:  { label: "已完成", color: "bg-green-100 text-green-800" },
  failed:     { label: "失败",   color: "bg-red-100 text-red-800" },
};

/* ---------- 页面组件 ---------- */

export default function TextToSpeechPage() {
  /* 表单状态 */
  const [inputMode, setInputMode] = useState<"text" | "file">("text");
  const [text, setText] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("zh");
  const [voiceId, setVoiceId] = useState("zh-CN-XiaoxiaoNeural");
  const [rate, setRate] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [volume, setVolume] = useState(0);
  const [outputFormat, setOutputFormat] = useState("mp3");

  /* 文件 & 任务状态 */
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<TTSTask[]>([]);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  /* 音色列表 */
  const [voices, setVoices] = useState<Voice[]>([]);
  const [filteredVoices, setFilteredVoices] = useState<Voice[]>([]);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  /* ---- 加载数据 ---- */
  useEffect(() => { loadVoices(); loadTasks(); }, []);

  useEffect(() => {
    if (selectedLanguage && voices.length > 0) {
      const filtered = voices.filter(v => v.language === selectedLanguage);
      setFilteredVoices(filtered);
      if (filtered.length > 0) setVoiceId(filtered[0].voice_id);
    } else {
      setFilteredVoices(voices);
    }
  }, [selectedLanguage, voices]);

  const loadVoices = async () => {
    try {
      const response = await apiClient.get('/tts/voices');
      setVoices(response.data.voices || []);
    } catch (error) {
      console.error('加载音色列表失败:', error);
    }
  };

  const loadTasks = async () => {
    try {
      const response = await apiClient.get('/tts/tasks');
      setTasks(response.data.tasks || []);
    } catch (error) {
      console.error('加载任务列表失败:', error);
    }
  };

  /* ---- 文件选择 ---- */
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    const validFiles = files.filter(file => {
      if (file.type !== "text/plain") { alert(`${file.name} 不是 .txt 文件`); return false; }
      if (file.size > 5 * 1024 * 1024) { alert(`${file.name} 文件大小超过 5MB`); return false; }
      return true;
    });
    setSelectedFiles(validFiles.length > 10 ? validFiles.slice(0, 10) : validFiles);
  };

  /* ---- 提交 ---- */
  const handleSubmit = async () => {
    setLoading(true);
    try {
      if (inputMode === "text") {
        if (!text || text.length < 1) { alert("请输入文字内容"); setLoading(false); return; }
        const formData = new FormData();
        formData.append("text", text);
        formData.append("voice_id", voiceId);
        formData.append("rate", String(rate));
        formData.append("pitch", `+${Math.round(pitch)}Hz`);
        formData.append("volume", `+${Math.round(volume)}%`);
        formData.append("output_format", outputFormat);
        const res = await apiClient.post("/tts/convert", formData, { headers: { "Content-Type": "multipart/form-data" } });
        pollTaskStatus(res.data.task_id);
        setText("");
      } else {
        if (selectedFiles.length === 0) { alert("请选择至少一个 .txt 文件"); setLoading(false); return; }
        for (const file of selectedFiles) {
          const formData = new FormData();
          formData.append("file", file);
          formData.append("voice_id", voiceId);
          formData.append("rate", String(rate));
          formData.append("output_format", outputFormat);
          const res = await apiClient.post("/tts/batch", formData, { headers: { "Content-Type": "multipart/form-data" } });
          pollTaskStatus(res.data.task_id);
        }
        setSelectedFiles([]);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "生成失败");
    } finally {
      setLoading(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/tts/task/${taskId}`);
        const taskData: TTSTask = response.data.task;
        setTasks(prev => {
          const idx = prev.findIndex(t => t.task_id === taskId);
          if (idx >= 0) { const n = [...prev]; n[idx] = taskData; return n; }
          return [taskData, ...prev];
        });
        if (taskData.status === "completed" || taskData.status === "failed") clearInterval(interval);
      } catch { clearInterval(interval); }
    }, 2000);
  };

  const getStatus = (s: string) => STATUS_MAP[s] || { label: s, color: "bg-gray-100 text-gray-800" };

  /* ---- 统计 ---- */
  const stats = [
    { label: "总任务数", value: tasks.length, color: "text-indigo-600" },
    { label: "已完成", value: tasks.filter(t => t.status === "completed").length, color: "text-green-600" },
    { label: "生成中", value: tasks.filter(t => t.status === "processing").length, color: "text-blue-600" },
    { label: "失败", value: tasks.filter(t => t.status === "failed").length, color: "text-red-500" },
  ];

  /* ---- 渲染 ---- */
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">🔊 AI 文字转语音 (TTS)</h1>
          <p className="text-gray-500 mt-1">将文本转换为自然流畅的语音，支持多种语言和音色</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {stats.map((s) => (
            <div key={s.label} className="bg-white rounded-xl p-4 text-center shadow-sm">
              <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-sm text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* 主体：单栏布局 */}
        <div className="space-y-6">
          {/* ===== 创建语音 ===== */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🔊 创建语音</h2>

            {/* 输入方式切换 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">输入方式</label>
              <div className="flex gap-3">
                {(["text", "file"] as const).map((m) => (
                  <button key={m} onClick={() => { setInputMode(m); setSelectedFiles([]); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${inputMode === m ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                  >
                    {m === "text" ? "✍️ 文字输入" : "📄 批量上传 .txt"}
                  </button>
                ))}
              </div>
            </div>

            {/* 文字输入 */}
            {inputMode === "text" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">文字内容</label>
                <textarea value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="请输入要转换为语音的文字内容...&#10;&#10;例如：你好，这是一段测试文本。欢迎使用 AI 文字转语音功能！"
                  className="w-full px-3 py-2 border rounded-lg h-36 resize-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 outline-none"
                  maxLength={5000}
                />
                <div className="text-xs text-gray-400 text-right mt-1">{text.length}/5000</div>
              </div>
            )}

            {/* 文件上传 */}
            {inputMode === "file" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">上传文本文件</label>
                <input ref={fileInputRef} type="file" accept=".txt" multiple onChange={handleFileSelect} className="hidden" />
                <button onClick={() => fileInputRef.current?.click()}
                  className="w-full px-4 py-3 border-2 border-dashed rounded-lg text-gray-500 hover:border-indigo-400 hover:text-indigo-500 transition-all"
                >
                  📤 选择 .txt 文件（最多10个，单个最大 5MB）
                </button>
                {selectedFiles.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {selectedFiles.map((file, idx) => (
                      <div key={idx} className="px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm">
                        ✅ {file.name}（{(file.size / 1024).toFixed(1)} KB）
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 语言 & 音色 */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-2">语言</label>
                <select value={selectedLanguage} onChange={(e) => setSelectedLanguage(e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                  {LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">音色</label>
                <select value={voiceId} onChange={(e) => setVoiceId(e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                  {filteredVoices.map((v) => <option key={v.voice_id} value={v.voice_id}>{v.name}</option>)}
                </select>
              </div>
            </div>

            {/* 语速 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">语速: {rate}x</label>
              <input type="range" min={0.8} max={1.5} step={0.1} value={rate} onChange={(e) => setRate(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
              <div className="flex justify-between text-xs text-gray-400 mt-1"><span>0.8x 慢速</span><span>1.0x 正常</span><span>1.5x 极快</span></div>
            </div>

            {/* 音调 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">音调: {pitch > 0 ? "+" : ""}{pitch}Hz</label>
              <input type="range" min={-50} max={50} step={5} value={pitch} onChange={(e) => setPitch(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
              <div className="flex justify-between text-xs text-gray-400 mt-1"><span>-50Hz 低沉</span><span>0 正常</span><span>+50Hz 尖锐</span></div>
            </div>

            {/* 音量 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">音量: {volume > 0 ? "+" : ""}{volume}%</label>
              <input type="range" min={-50} max={50} step={5} value={volume} onChange={(e) => setVolume(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
              <div className="flex justify-between text-xs text-gray-400 mt-1"><span>-50% 小</span><span>0 正常</span><span>+50% 大</span></div>
            </div>

            {/* 输出格式 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">输出格式</label>
              <div className="flex gap-3">
                {(["mp3", "wav"] as const).map((f) => (
                  <button key={f} onClick={() => setOutputFormat(f)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${outputFormat === f ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                  >
                    {f === "mp3" ? "MP3 (推荐)" : "WAV (高质量)"}
                  </button>
                ))}
              </div>
            </div>

            {/* 提交按钮 */}
            <button onClick={handleSubmit} disabled={loading}
              className="w-full mt-2 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
            >
              {loading ? "生成中..." : inputMode === "text" ? "🚀 生成语音" : `🚀 批量生成 (${selectedFiles.length} 个文件)`}
            </button>
          </div>


          {/* ===== 任务列表（底部） ===== */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📋 生成任务</h2>

            {tasks.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <div className="text-6xl mb-4 opacity-50">🔊</div>
                <h3 className="text-lg font-medium">暂无生成任务</h3>
                <p>在上方输入文字开始生成语音</p>
              </div>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => {
                  const st = getStatus(task.status);
                  const isExpanded = expandedTask === task.task_id;
                  return (
                    <div key={task.task_id} className="border rounded-xl p-5">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-1">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${st.color}`}>{st.label}</span>
                            {task.voice_id && (
                              <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                                {voices.find(v => v.voice_id === task.voice_id)?.name || task.voice_id}
                              </span>
                            )}
                          </div>
                          {task.text && (
                            <p className="text-sm text-gray-600 mt-1">
                              {task.text.substring(0, 80)}{task.text.length > 80 ? "..." : ""}
                            </p>
                          )}
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
                            <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all" style={{ width: `${Math.round(task.progress * 100)}%` }} />
                          </div>
                        </div>
                      )}

                      {/* 错误信息 */}
                      {task.error_message && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm mt-3">
                          ❌ {task.error_message}
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
                              <p className="mt-1">{voices.find(v => v.voice_id === task.voice_id)?.name || task.voice_id || "—"}</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-3">
                              <span className="text-gray-500">创建时间</span>
                              <p className="mt-1">{new Date(task.created_at).toLocaleString("zh-CN")}</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-3">
                              <span className="text-gray-500">音频文件</span>
                              <p className="mt-1 truncate">{task.audio_file || "—"}</p>
                            </div>
                          </div>

                          {/* 完整文本 */}
                          {task.text && (
                            <div className="bg-gray-50 rounded-lg p-3 mb-4">
                              <span className="text-gray-500 text-sm">完整文本</span>
                              <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{task.text}</p>
                            </div>
                          )}

                          {/* 音频播放 & 下载 */}
                          {task.status === "completed" && task.audio_file && (
                            <div className="flex gap-2">
                              <button
                                onClick={async () => {
                                  try {
                                    const res = await fetch(`${API_BASE_URL}/api/v1/tts/download/${task.audio_file}`);
                                    const data = await res.json();
                                    if (data.download_url) { const audio = new Audio(data.download_url); audio.play(); }
                                    else alert("获取播放链接失败");
                                  } catch { alert("获取播放链接失败"); }
                                }}
                                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
                              >
                                ▶ 播放
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    const res = await fetch(`${API_BASE_URL}/api/v1/tts/download/${task.audio_file}`);
                                    const data = await res.json();
                                    if (data.download_url) window.open(data.download_url, "_blank");
                                    else alert("获取下载链接失败");
                                  } catch { alert("获取下载链接失败"); }
                                }}
                                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                              >
                                📥 下载
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    const res = await fetch(`${API_BASE_URL}/api/v1/tts/download/${task.audio_file}`);
                                    const data = await res.json();
                                    if (data.download_url) {
                                      const a = document.createElement("a");
                                      a.href = data.download_url;
                                      a.download = task.audio_file!;
                                      a.style.display = "none";
                                      document.body.appendChild(a);
                                      a.click();
                                      document.body.removeChild(a);
                                    } else alert("获取导出链接失败");
                                  } catch { alert("导出失败"); }
                                }}
                                className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700"
                              >
                                💾 导出保存
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="text-sm text-gray-400 mt-3 pt-3 border-t">
                        ⏰ {new Date(task.created_at).toLocaleString("zh-CN")}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* ===== 使用说明 ===== */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📖 使用说明</h2>
            <div className="text-sm leading-7 text-gray-600">
              <h3 className="text-base font-semibold text-gray-800 mt-0">✨ 功能特性</h3>
              <ul className="list-disc pl-5 mb-4">
                <li><strong>多语言支持：</strong>支持 11 种语言，包括中文、英语、日语、韩语等</li>
                <li><strong>丰富音色：</strong>40+ 专业音色，男声/女声/中性音色可选</li>
                <li><strong>灵活调节：</strong>支持语速（0.8x-1.5x）、音调（±50Hz）、音量（±50%）调节</li>
                <li><strong>批量处理：</strong>支持批量上传 .txt 文件，最多 10 个文件</li>
                <li><strong>多种格式：</strong>支持 MP3（体积小）和 WAV（高质量）格式</li>
              </ul>
              <h3 className="text-base font-semibold text-gray-800">🎤 推荐音色</h3>
              <ul className="list-disc pl-5 mb-4">
                <li><strong>简体中文：</strong>晓晓（温柔）、云希（阳光）、云扬（成熟）、晓伊（知性）</li>
                <li><strong>英语：</strong>Jenny（友好）、Guy（专业）、Aria（自然）</li>
                <li><strong>日语：</strong>七海、圭太、葵</li>
                <li><strong>韩语：</strong>선희、인준、봉진</li>
              </ul>
              <h3 className="text-base font-semibold text-gray-800">💡 使用技巧</h3>
              <ul className="list-disc pl-5">
                <li><strong>文本输入：</strong>适合短文本快速转换，最多 5000 字符</li>
                <li><strong>批量上传：</strong>适合长文本或多个文本文件，自动按段落分割</li>
                <li><strong>语速建议：</strong>有声读物 0.9-1.0x，新闻播报 1.0-1.1x，快速浏览 1.2-1.3x</li>
                <li><strong>文件格式：</strong>使用 UTF-8 编码保存 .txt 文件，避免乱码</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
