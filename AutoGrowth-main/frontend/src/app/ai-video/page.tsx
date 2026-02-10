"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import apiClient from "@/lib/api-client";

/* ---------- 类型 ---------- */

interface VideoTask {
  task_id: string;
  status: string;
  progress: number;
  video_url?: string;
  thumbnail_url?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

/* ---------- 常量 ---------- */

const STYLE_OPTIONS = [
  { value: "realistic", label: "真人写实风" },
  { value: "anime", label: "动漫风" },
  { value: "drama", label: "短剧质感风" },
  { value: "cinematic", label: "电影感" },
  { value: "cartoon", label: "卡通风" },
];

const RATIO_OPTIONS = [
  { value: "9:16", label: "竖屏 (9:16)" },
  { value: "16:9", label: "横屏 (16:9)" },
  { value: "1:1", label: "方形 (1:1)" },
];

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending:    { label: "等待中", color: "bg-yellow-100 text-yellow-800" },
  processing: { label: "生成中", color: "bg-blue-100 text-blue-800" },
  completed:  { label: "已完成", color: "bg-green-100 text-green-800" },
  failed:     { label: "失败",   color: "bg-red-100 text-red-800" },
};

/* ---------- 页面组件 ---------- */

export default function AIVideoPage() {
  /* 表单状态 */
  const [inputMode, setInputMode] = useState<"text" | "file">("text");
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("realistic");
  const [duration, setDuration] = useState(10);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [characterDesc, setCharacterDesc] = useState("");
  const [sceneDesc, setSceneDesc] = useState("");
  const [cameraMovement, setCameraMovement] = useState("");
  const [audioStyle, setAudioStyle] = useState("");

  /* 文件 & 任务状态 */
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<VideoTask[]>([]);
  const [previewTask, setPreviewTask] = useState<VideoTask | null>(null);

  /* ---- 加载任务列表（从后端恢复，切换模块不丢失） ---- */
  const loadTasks = useCallback(async () => {
    try {
      const res = await apiClient.get("/ai-video/tasks");
      const items = res.data.items || res.data.tasks || [];
      setTasks(items);
    } catch (error) {
      console.error("加载视频任务列表失败:", error);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 5000);
    return () => clearInterval(interval);
  }, [loadTasks]);

  /* ---- 工具函数 ---- */

  const readFileContent = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = reject;
      reader.readAsText(file);
    });

  const getStatus = (s: string) => STATUS_MAP[s] || { label: s, color: "bg-gray-100 text-gray-800" };

  /* ---- 业务逻辑 ---- */

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "text/plain") { alert("请上传 .txt 文件"); return; }
    if (file.size > 5 * 1024 * 1024) { alert("文件不能超过 5MB"); return; }
    setSelectedFile(file);
  };

  const handleSubmit = async () => {
    let finalPrompt = prompt;
    if (inputMode === "file") {
      if (!selectedFile) { alert("请选择 .txt 文件"); return; }
      finalPrompt = await readFileContent(selectedFile);
    }
    if (!finalPrompt || finalPrompt.length < 10) { alert("描述至少需要 10 个字符"); return; }

    setLoading(true);
    try {
      const res = await apiClient.post("/ai-video/generate", {
        prompt: finalPrompt, style, duration, aspect_ratio: aspectRatio,
        character_description: characterDesc || undefined,
        scene_description: sceneDesc || undefined,
        camera_movement: cameraMovement || undefined,
        audio_style: audioStyle || undefined,
      });
      const newTask: VideoTask = { task_id: res.data.task_id, status: res.data.status, progress: 0, created_at: new Date().toISOString() };
      setTasks((prev) => [newTask, ...prev]);
      pollTaskStatus(res.data.task_id);
      setPrompt(""); setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      alert(err.response?.data?.detail || "生成失败");
    } finally {
      setLoading(false);
    }
  };

  const pollTaskStatus = (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/ai-video/tasks/${taskId}`);
        const data: VideoTask = res.data;
        setTasks((prev) => prev.map((t) => (t.task_id === taskId ? data : t)));
        if (data.status === "completed" || data.status === "failed") clearInterval(interval);
      } catch { clearInterval(interval); }
    }, 3000);
  };

  /* ---- 统计 ---- */
  const stats = [
    { label: "总任务数", value: tasks.length, color: "text-indigo-600" },
    { label: "已完成", value: tasks.filter((t) => t.status === "completed").length, color: "text-green-600" },
    { label: "生成中", value: tasks.filter((t) => t.status === "processing").length, color: "text-blue-600" },
    { label: "失败", value: tasks.filter((t) => t.status === "failed").length, color: "text-red-500" },
  ];

  /* ---- 渲染 ---- */
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">🎬 AI 视频生成</h1>
          <p className="text-gray-500 mt-1">输入文字描述或上传脚本，AI 自动生成短视频</p>
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
          {/* ===== 创建视频 ===== */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🎬 创建视频</h2>

            {/* 输入方式切换 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">输入方式</label>
              <div className="flex gap-3">
                {(["text", "file"] as const).map((m) => (
                  <button key={m} onClick={() => { setInputMode(m); setSelectedFile(null); }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${inputMode === m ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                  >
                    {m === "text" ? "✍️ 文字描述" : "📄 上传 .txt"}
                  </button>
                ))}
              </div>
            </div>

            {/* 文字描述 */}
            {inputMode === "text" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">文字描述</label>
                <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)}
                  placeholder="例如：一个年轻女孩在咖啡厅里看书，突然接到一个神秘电话..."
                  className="w-full px-3 py-2 border rounded-lg h-28 resize-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 outline-none"
                  maxLength={2000}
                />
                <div className="text-xs text-gray-400 text-right mt-1">{prompt.length}/2000</div>
              </div>
            )}

            {/* 文件上传 */}
            {inputMode === "file" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">上传文本文件</label>
                <input ref={fileInputRef} type="file" accept=".txt" onChange={handleFileSelect} className="hidden" />
                <button onClick={() => fileInputRef.current?.click()}
                  className="w-full px-4 py-3 border-2 border-dashed rounded-lg text-gray-500 hover:border-indigo-400 hover:text-indigo-500 transition-all"
                >
                  📤 选择 .txt 文件（最大 5MB）
                </button>
                {selectedFile && (
                  <div className="mt-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm">
                    ✅ {selectedFile.name}（{(selectedFile.size / 1024).toFixed(1)} KB）
                  </div>
                )}
              </div>
            )}

            {/* 风格 & 比例 */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-2">画风风格</label>
                <select value={style} onChange={(e) => setStyle(e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                  {STYLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">视频比例</label>
                <select value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                  {RATIO_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>

            {/* 时长 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">视频时长: {duration}s</label>
              <input type="range" min={3} max={60} value={duration} onChange={(e) => setDuration(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
              <div className="flex justify-between text-xs text-gray-400 mt-1"><span>3s</span><span>30s</span><span>60s</span></div>
            </div>

            {/* 可选参数 */}
            {[
              { label: "人物设定（可选）", value: characterDesc, set: setCharacterDesc, ph: "例如：20岁左右的亚洲女性，长发，穿着休闲" },
              { label: "场景要求（可选）", value: sceneDesc, set: setSceneDesc, ph: "例如：温馨的咖啡厅，下午阳光透过窗户" },
              { label: "镜头语言（可选）", value: cameraMovement, set: setCameraMovement, ph: "例如：从远景推进到中景特写" },
              { label: "音频风格（可选）", value: audioStyle, set: setAudioStyle, ph: "例如：轻柔的背景音乐" },
            ].map((field) => (
              <div key={field.label} className="mb-3">
                <label className="block text-sm font-medium mb-1">{field.label}</label>
                <input type="text" value={field.value} onChange={(e) => field.set(e.target.value)}
                  placeholder={field.ph} className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
            ))}

            {/* 提交按钮 */}
            <button onClick={handleSubmit} disabled={loading}
              className="w-full mt-2 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
            >
              {loading ? "生成中..." : "🚀 开始生成视频"}
            </button>
          </div>

          {/* ===== 任务列表（底部） ===== */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📋 生成任务</h2>

            {tasks.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <div className="text-6xl mb-4 opacity-50">🎬</div>
                <h3 className="text-lg font-medium">暂无生成任务</h3>
                <p>在上方输入描述开始生成视频</p>
              </div>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => {
                  const st = getStatus(task.status);
                  const isSelected = previewTask?.task_id === task.task_id;
                  return (
                    <div key={task.task_id} className="border rounded-xl p-5">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-1">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${st.color}`}>{st.label}</span>
                            <span className="text-xs text-gray-400">ID: {task.task_id.substring(0, 8)}...</span>
                          </div>
                          <p className="text-sm text-gray-500 mt-1">
                            创建时间: {new Date(task.created_at).toLocaleString("zh-CN")}
                            {task.completed_at && ` | 完成时间: ${new Date(task.completed_at).toLocaleString("zh-CN")}`}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          {task.status === "processing" && (
                            <span className="text-sm text-gray-500">{task.progress}%</span>
                          )}
                          <button
                            onClick={() => setPreviewTask(isSelected ? null : task)}
                            className={`px-4 py-2 rounded-lg text-sm ${isSelected ? "bg-gray-200 text-gray-700" : "bg-indigo-600 text-white hover:bg-indigo-700"}`}
                          >
                            {isSelected ? "收起详情" : "查看详情"}
                          </button>
                        </div>
                      </div>

                      {/* 进度条 */}
                      {(task.status === "processing" || task.status === "pending") && (
                        <div className="mt-3">
                          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all" style={{ width: `${task.progress}%` }} />
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
                      {isSelected && (
                        <div className="mt-4 border-t pt-4">
                          <h4 className="font-medium mb-3">📄 任务详情</h4>
                          <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                            <div className="bg-gray-50 rounded-lg p-3">
                              <span className="text-gray-500">任务ID</span>
                              <p className="font-mono text-xs mt-1">{task.task_id}</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-3">
                              <span className="text-gray-500">状态</span>
                              <p className="mt-1">{st.label}</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-3">
                              <span className="text-gray-500">创建时间</span>
                              <p className="mt-1">{new Date(task.created_at).toLocaleString("zh-CN")}</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-3">
                              <span className="text-gray-500">完成时间</span>
                              <p className="mt-1">{task.completed_at ? new Date(task.completed_at).toLocaleString("zh-CN") : "—"}</p>
                            </div>
                          </div>

                          {/* 视频预览 & 下载 */}
                          {task.status === "completed" && (
                            <div>
                              {task.video_url && (
                                <div className="mb-3 rounded-lg overflow-hidden bg-black">
                                  <video src={task.video_url} controls className="w-full max-h-[400px]" />
                                </div>
                              )}
                              <div className="flex gap-2">
                                <button onClick={async () => {
                                    try {
                                      const res = await apiClient.get(`/ai-video/download/${task.task_id}`);
                                      const url = res.data.download_url;
                                      if (url) {
                                        const a = document.createElement("a");
                                        a.href = url;
                                        a.download = `video_${task.task_id.substring(0, 8)}.mp4`;
                                        a.style.display = "none";
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                      }
                                    } catch (err: any) {
                                      alert(err.response?.data?.detail || "下载失败，视频文件可能尚未生成");
                                    }
                                  }}
                                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
                                  📥 下载视频
                                </button>
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
    </div>
  );
}

