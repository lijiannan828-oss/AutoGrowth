"use client";

import { useState, useEffect, useCallback } from "react";
import apiClient from "@/lib/api-client";

interface Voice {
  voice_id: string;
  name: string;
  language: string;
  gender: string;
}

interface DialogueSegment {
  role: string;
  text: string;
}

interface RoleConfig {
  voice_id: string;
  rate: number;
  pitch: string;
  volume: string;
}

interface TTSTask {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  text: string;
  type?: string;
  roles?: string[];
  segment_count?: number;
  audio_file?: string;
  filename?: string;
  created_at: string;
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

const ROLE_COLORS = [
  "bg-blue-100 text-blue-800 border-blue-300",
  "bg-green-100 text-green-800 border-green-300",
  "bg-purple-100 text-purple-800 border-purple-300",
  "bg-orange-100 text-orange-800 border-orange-300",
  "bg-pink-100 text-pink-800 border-pink-300",
  "bg-teal-100 text-teal-800 border-teal-300",
  "bg-yellow-100 text-yellow-800 border-yellow-300",
  "bg-red-100 text-red-800 border-red-300",
];

// ---- 子组件：展开音频操作面板 ----
function ExpandedAudioPanel({ task }: { task: TTSTask }) {
  return (
    <div className="mt-4 border-t pt-4">
      <h4 className="font-medium mb-3">🎧 音频操作</h4>
      <div className="flex gap-2">
        <button
          onClick={async () => {
            try {
              const res = await apiClient.get(`/tts/download/${task.audio_file}`);
              if (res.data.download_url) {
                const audio = new Audio(res.data.download_url);
                audio.play().catch(() => alert("播放失败"));
              }
            } catch { alert("获取播放链接失败"); }
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
                const a = document.createElement("a");
                a.href = res.data.download_url;
                a.download = `${task.filename || task.task_id}.mp3`;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              }
            } catch { alert("下载失败"); }
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
            } catch { alert("预览失败"); }
          }}
          className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-lg hover:bg-gray-200"
        >
          👁 预览
        </button>
      </div>
    </div>
  );
}

// ---- 子组件：状态标签 ----
function StatusBadge({ status, progress }: { status: string; progress: number }) {
  const colorMap: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  const labelMap: Record<string, string> = {
    pending: "🕐 等待处理",
    processing: "⏳ 处理中",
    completed: "✅ 已完成",
    failed: "❌ 失败",
  };
  return (
    <div className="text-right">
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${colorMap[status] || ""}`}>
        {labelMap[status] || status}
      </span>
      <p className="text-sm text-gray-500 mt-1">{progress}%</p>
    </div>
  );
}

// ---- 子组件：对话任务列表 ----
function DialogueTaskList({
  tasks, expandedTask, setExpandedTask,
}: {
  tasks: TTSTask[];
  expandedTask: string | null;
  setExpandedTask: (id: string | null) => void;
}) {
  if (tasks.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 text-center py-16 text-gray-400">
        <div className="text-6xl mb-4 opacity-50">🎭</div>
        <h3 className="text-lg font-medium">暂无对话任务</h3>
        <p>输入对话文本并配置角色音色后开始合成</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">📋 对话任务</h2>
      <div className="space-y-4">
        {tasks.map((task) => {
          const isExpanded = expandedTask === task.task_id;
          return (
            <div key={task.task_id} className="border rounded-xl p-5">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold">
                    🎭 {task.filename || task.text}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {task.roles?.join("、")} | {task.segment_count}段
                    | {new Date(task.created_at).toLocaleString("zh-CN")}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={task.status} progress={task.progress} />
                  <button
                    onClick={() => setExpandedTask(isExpanded ? null : task.task_id)}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
                  >
                    {isExpanded ? "收起" : "详情"}
                  </button>
                </div>
              </div>

              {task.status === "failed" && task.error_message && (
                <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                  {task.error_message}
                </div>
              )}

              {task.status === "processing" && (
                <div className="mt-3">
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {isExpanded && task.status === "completed" && task.audio_file && (
                <ExpandedAudioPanel task={task} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---- 子组件：全局设置 + 对话预览 + 提交按钮 ----
function DialoguePreviewAndSubmit({
  segments, getRoleColor, silenceGap, setSilenceGap,
  outputFormat, setOutputFormat, submitting, handleSubmit,
}: {
  segments: DialogueSegment[];
  getRoleColor: (role: string) => string;
  silenceGap: number;
  setSilenceGap: (v: number) => void;
  outputFormat: string;
  setOutputFormat: (v: string) => void;
  submitting: boolean;
  handleSubmit: () => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">⚙️ 全局设置 &amp; 预览</h2>

      {/* 全局参数 */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium mb-1">
            句间静音: {silenceGap}ms
          </label>
          <input
            type="range" min="0" max="3000" step="100"
            value={silenceGap}
            onChange={(e) => setSilenceGap(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0ms</span><span>3000ms</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">输出格式</label>
          <select
            value={outputFormat}
            onChange={(e) => setOutputFormat(e.target.value)}
            className="w-full p-2 border rounded-lg"
          >
            <option value="mp3">MP3</option>
            <option value="wav">WAV</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-8 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
          >
            {submitting ? "提交中..." : "🚀 开始合成"}
          </button>
        </div>
      </div>

      {/* 对话预览 */}
      <h3 className="text-sm font-semibold mb-2 text-gray-600">对话预览</h3>
      <div className="max-h-64 overflow-y-auto space-y-1 border rounded-lg p-3 bg-gray-50">
        {segments.map((seg, idx) => (
          <div key={idx} className="flex gap-2 text-sm">
            <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium border ${getRoleColor(seg.role)}`}>
              {seg.role}
            </span>
            <span className="text-gray-700">{seg.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DialogueMode() {
  // 文本与解析
  const [text, setText] = useState("");
  const [segments, setSegments] = useState<DialogueSegment[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [roleConfigs, setRoleConfigs] = useState<Record<string, RoleConfig>>({});

  // 音色数据
  const [selectedLanguage, setSelectedLanguage] = useState("zh");
  const [voices, setVoices] = useState<Voice[]>([]);

  // 全局设置
  const [silenceGap, setSilenceGap] = useState(500);
  const [outputFormat, setOutputFormat] = useState("mp3");

  // 状态
  const [parsing, setParsing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [tasks, setTasks] = useState<TTSTask[]>([]);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  // 加载音色列表
  useEffect(() => {
    apiClient.get(`/tts/voices?language=${selectedLanguage}`)
      .then((res) => {
        setVoices(res.data.voices || []);
      })
      .catch(console.error);
  }, [selectedLanguage]);

  // 轮询任务
  const loadTasks = useCallback(async () => {
    try {
      const res = await apiClient.get("/tts/tasks");
      const all: TTSTask[] = res.data.tasks || [];
      setTasks(all.filter((t) => t.type === "dialogue"));
    } catch (error) {
      console.error("加载任务失败:", error);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 2000);
    return () => clearInterval(interval);
  }, [loadTasks]);

  // 解析角色
  const handleParse = async () => {
    if (!text.trim()) return;
    setParsing(true);
    try {
      const formData = new FormData();
      formData.append("text", text.trim());
      const res = await apiClient.post("/tts/dialogue/parse", formData);
      const parsed = res.data;
      setSegments(parsed.segments || []);
      setRoles(parsed.roles || []);

      // 为每个角色初始化默认配置
      const configs: Record<string, RoleConfig> = {};
      (parsed.roles || []).forEach((role: string, idx: number) => {
        configs[role] = roleConfigs[role] || {
          voice_id: voices.length > 0
            ? voices[idx % voices.length].voice_id
            : "",
          rate: 1.0,
          pitch: "+0Hz",
          volume: "+0%",
        };
      });
      setRoleConfigs(configs);
    } catch (error) {
      console.error("解析失败:", error);
      alert("解析对话文本失败");
    } finally {
      setParsing(false);
    }
  };

  // 更新角色配置
  const updateRoleConfig = (role: string, field: keyof RoleConfig, value: string | number) => {
    setRoleConfigs((prev) => ({
      ...prev,
      [role]: { ...prev[role], [field]: value },
    }));
  };

  // 获取角色颜色
  const getRoleColor = (role: string) => {
    const idx = roles.indexOf(role);
    return ROLE_COLORS[idx % ROLE_COLORS.length];
  };

  // 上传 txt 文件填充文本
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const content = await file.text();
    setText(content);
  };

  // 提交多角色对话任务
  const handleSubmit = async () => {
    if (segments.length === 0) {
      alert("请先解析对话文本");
      return;
    }
    const missingVoice = roles.find((r) => !roleConfigs[r]?.voice_id);
    if (missingVoice) {
      alert(`角色「${missingVoice}」尚未配置音色`);
      return;
    }

    setSubmitting(true);
    try {
      const roleVoices: Record<string, RoleConfig> = {};
      roles.forEach((r) => { roleVoices[r] = roleConfigs[r]; });

      await apiClient.post("/tts/dialogue", {
        text: text.trim(),
        role_voices: roleVoices,
        silence_gap: silenceGap,
        output_format: outputFormat,
      });
      loadTasks();
    } catch (error) {
      console.error("提交失败:", error);
      alert("提交对话任务失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 文本输入区 */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🎭 对话文本</h2>
        <p className="text-sm text-gray-500 mb-3">
          格式：每行 <code className="bg-gray-100 px-1 rounded">角色名: 对话内容</code>，无角色前缀的行视为旁白
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={"小明: 你好，今天天气真好\n小红: 是啊，我们去公园吧\n旁白: 于是他们一起出发了\n小明: 走吧！"}
          rows={10}
          className="w-full p-4 border rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
        />
        <div className="flex items-center gap-3 mt-3">
          <label className="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg cursor-pointer hover:bg-gray-200 text-sm">
            📂 导入 TXT 文件
            <input type="file" accept=".txt" className="hidden" onChange={handleFileUpload} />
          </label>
          <button
            onClick={handleParse}
            disabled={!text.trim() || parsing}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium disabled:opacity-50 hover:bg-indigo-700"
          >
            {parsing ? "解析中..." : "🔍 解析角色"}
          </button>
          <span className="text-sm text-gray-400">
            {segments.length > 0 && `已解析 ${segments.length} 段对话，${roles.length} 个角色`}
          </span>
        </div>
      </div>

      {/* 角色配置区 */}
      {roles.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🎤 角色音色配置</h2>

          {/* 语言选择 */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">语言（影响可选音色）</label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="w-48 p-2 border rounded-lg"
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>{lang.name}</option>
              ))}
            </select>
          </div>

          {/* 逐角色配置 */}
          <div className="space-y-4">
            {roles.map((role) => (
              <div key={role} className={`border rounded-xl p-4 ${getRoleColor(role)}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="font-semibold text-base">{role}</span>
                  <span className="text-xs opacity-70">
                    ({segments.filter((s) => s.role === role).length} 句)
                  </span>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* 音色选择 */}
                  <div>
                    <label className="block text-xs font-medium mb-1">音色</label>
                    <select
                      value={roleConfigs[role]?.voice_id || ""}
                      onChange={(e) => updateRoleConfig(role, "voice_id", e.target.value)}
                      className="w-full p-2 border rounded-lg bg-white text-sm"
                    >
                      <option value="">请选择</option>
                      {voices.map((v) => (
                        <option key={v.voice_id} value={v.voice_id}>
                          {v.name} {v.gender === "male" ? "♂" : "♀"}
                        </option>
                      ))}
                    </select>
                  </div>
                  {/* 语速 */}
                  <div>
                    <label className="block text-xs font-medium mb-1">
                      语速: {roleConfigs[role]?.rate?.toFixed(1) || "1.0"}x
                    </label>
                    <input
                      type="range" min="0.5" max="2.0" step="0.1"
                      value={roleConfigs[role]?.rate || 1.0}
                      onChange={(e) => updateRoleConfig(role, "rate", parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/50 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>
                  {/* 音调 */}
                  <div>
                    <label className="block text-xs font-medium mb-1">音调</label>
                    <select
                      value={roleConfigs[role]?.pitch || "+0Hz"}
                      onChange={(e) => updateRoleConfig(role, "pitch", e.target.value)}
                      className="w-full p-2 border rounded-lg bg-white text-sm"
                    >
                      <option value="-20Hz">很低</option>
                      <option value="-10Hz">偏低</option>
                      <option value="+0Hz">默认</option>
                      <option value="+10Hz">偏高</option>
                      <option value="+20Hz">很高</option>
                    </select>
                  </div>
                  {/* 音量 */}
                  <div>
                    <label className="block text-xs font-medium mb-1">音量</label>
                    <select
                      value={roleConfigs[role]?.volume || "+0%"}
                      onChange={(e) => updateRoleConfig(role, "volume", e.target.value)}
                      className="w-full p-2 border rounded-lg bg-white text-sm"
                    >
                      <option value="-30%">低</option>
                      <option value="-15%">偏低</option>
                      <option value="+0%">默认</option>
                      <option value="+15%">偏高</option>
                      <option value="+30%">高</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 全局设置 + 对话预览 + 提交 — 下一段继续 */}
      {segments.length > 0 && (
        <DialoguePreviewAndSubmit
          segments={segments}
          getRoleColor={getRoleColor}
          silenceGap={silenceGap}
          setSilenceGap={setSilenceGap}
          outputFormat={outputFormat}
          setOutputFormat={setOutputFormat}
          submitting={submitting}
          handleSubmit={handleSubmit}
        />
      )}

      {/* 任务列表 */}
      <DialogueTaskList
        tasks={tasks}
        expandedTask={expandedTask}
        setExpandedTask={setExpandedTask}
      />
    </div>
  );
}

