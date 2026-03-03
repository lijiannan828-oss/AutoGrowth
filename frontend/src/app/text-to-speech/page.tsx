"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuthContext } from "@/context/AuthContext";
import apiClient from "@/lib/api-client";
import TTSTaskList from "./TTSTaskList";
import { VoicePreviewButton, FullPreviewButton } from "./PreviewButtons";

interface TTSSourceFile {
  file_id: string;
  display_name: string;
  original_filename: string;
  gcs_path: string;
  file_size: number;
  file_extension: string;
  uploaded_at: string;
}

interface Voice {
  voice_id: string;
  name: string;
  language: string;
  gender: string;
}

interface RoleConfig {
  voice_id: string;
  rate: number;
  pitch: string;
  volume: string;
}

interface DialogueSegment {
  role: string;
  text: string;
}

interface TTSTask {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  text: string;
  voice_id?: string;
  type?: string;
  roles?: string[];
  segment_count?: number;
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

const ROLE_COLORS = [
  "bg-blue-100 text-blue-800 border-blue-300",
  "bg-green-100 text-green-800 border-green-300",
  "bg-purple-100 text-purple-800 border-purple-300",
  "bg-orange-100 text-orange-800 border-orange-300",
  "bg-pink-100 text-pink-800 border-pink-300",
  "bg-teal-100 text-teal-800 border-teal-300",
];

export default function TTSPage() {
  const { user } = useAuthContext();

  // 源文件输入模式：选择已有 / 本地上传 / 手动文字 / 手动路径
  const [sourceMode, setSourceMode] = useState<"select" | "upload" | "text" | "manual">("select");
  // 文字输入内容
  const [textContent, setTextContent] = useState("");
  // 手动 GCS 路径
  const [manualPath, setManualPath] = useState("");
  // 选中的源文件 GCS 路径
  const [sourceFilePath, setSourceFilePath] = useState("");
  // 选中的源文件 ID
  const [sourceFileId, setSourceFileId] = useState("");

  // GCS 已上传文件列表
  const [gcsFiles, setGcsFiles] = useState<TTSSourceFile[]>([]);
  const [totalFiles, setTotalFiles] = useState(0);

  // 本地上传相关
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileDisplayName, setFileDisplayName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 文件下拉框
  const [fileDropdownOpen, setFileDropdownOpen] = useState(false);
  const [fileSearch, setFileSearch] = useState("");
  const [fileSortBy, setFileSortBy] = useState<"name" | "time">("time");
  const fileDropdownRef = useRef<HTMLDivElement>(null);

  // 重命名
  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [newDisplayName, setNewDisplayName] = useState("");

  // 任务命名
  const [taskName, setTaskName] = useState("");
  // 是否多角色对话
  const [isMultiRole, setIsMultiRole] = useState(false);
  // 语言模式：单语种 / 多语种
  const [languageMode, setLanguageMode] = useState<"single" | "multi">("single");

  // 音色相关
  const [selectedLanguage, setSelectedLanguage] = useState("zh");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState("");
  const [rate, setRate] = useState(1.0);
  const [pitch, setPitch] = useState("+0Hz");
  const [volume, setVolume] = useState("+0%");

  // 多角色相关
  const [segments, setSegments] = useState<DialogueSegment[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [roleConfigs, setRoleConfigs] = useState<Record<string, RoleConfig>>({});
  const [parsing, setParsing] = useState(false);

  // 全局设置
  const [silenceGap, setSilenceGap] = useState(500);
  const [outputFormat, setOutputFormat] = useState("mp3");

  // 任务列表
  const [tasks, setTasks] = useState<TTSTask[]>([]);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // --- 副作用 ---

  // 加载音色列表
  useEffect(() => {
    const url = languageMode === "multi"
      ? "/tts/voices"
      : `/tts/voices?language=${selectedLanguage}`;
    apiClient
      .get(url)
      .then((res) => {
        const v = res.data.voices || [];
        setVoices(v);
        if (v.length > 0 && !selectedVoice) {
          setSelectedVoice(v[0].voice_id);
        }
      })
      .catch(console.error);
  }, [selectedLanguage, languageMode]);

  // 轮询任务列表
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

  // --- GCS 文件列表 ---
  const loadGcsFiles = useCallback(async () => {
    try {
      const res = await apiClient.get("/tts/files");
      setGcsFiles(res.data.files || []);
      setTotalFiles(res.data.total || 0);
    } catch (error) {
      console.error("加载文件列表失败:", error);
    }
  }, []);

  useEffect(() => {
    loadGcsFiles();
  }, [loadGcsFiles]);

  // 点击外部关闭下拉框
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (fileDropdownRef.current && !fileDropdownRef.current.contains(e.target as Node)) {
        setFileDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // --- 本地上传到 GCS ---
  const handleLocalFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setFileDisplayName(file.name.replace(/\.[^.]+$/, ""));
    }
  };

  const handleUploadToGcs = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (fileDisplayName.trim()) {
        formData.append("display_name", fileDisplayName.trim());
      }
      await apiClient.post("/tts/upload", formData, {
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      setSelectedFile(null);
      setFileDisplayName("");
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadGcsFiles();
      setSourceMode("select");
    } catch (error) {
      console.error("上传失败:", error);
      alert("上传失败");
    } finally {
      setUploading(false);
    }
  };

  // --- 重命名 ---
  const handleRename = async (fileId: string) => {
    if (!newDisplayName.trim()) return;
    try {
      await apiClient.patch(`/tts/files/${fileId}`, { display_name: newDisplayName.trim() });
      setRenamingFileId(null);
      setNewDisplayName("");
      await loadGcsFiles();
    } catch (error) {
      console.error("重命名失败:", error);
      alert("重命名失败");
    }
  };

  // --- 文件列表过滤排序 ---
  const filteredFiles = gcsFiles
    .filter((f) => {
      if (!fileSearch.trim()) return true;
      const q = fileSearch.toLowerCase();
      return (f.display_name || "").toLowerCase().includes(q) || (f.original_filename || "").toLowerCase().includes(q);
    })
    .sort((a, b) => {
      if (fileSortBy === "name") return (a.display_name || "").localeCompare(b.display_name || "");
      return (b.uploaded_at || "").localeCompare(a.uploaded_at || "");
    });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // --- 多角色解析 ---
  const handleParse = async () => {
    setParsing(true);
    try {
      const formData = new FormData();

      if (sourceMode === "text") {
        if (!textContent.trim()) { alert("请输入文字内容"); setParsing(false); return; }
        formData.append("text", textContent.trim());
      } else if (sourceMode === "select") {
        if (!sourceFileId) { alert("请选择源文件"); setParsing(false); return; }
        formData.append("file_id", sourceFileId);
      } else if (sourceMode === "manual") {
        if (!manualPath.trim()) { alert("请输入 GCS 路径"); setParsing(false); return; }
        formData.append("gcs_path", manualPath.trim());
      } else {
        alert("请先上传文件后再解析"); setParsing(false); return;
      }

      const res = await apiClient.post("/tts/dialogue/parse", formData);
      const parsed = res.data;
      setSegments(parsed.segments || []);
      setRoles(parsed.roles || []);
      // 如果后端返回了文本内容（从文件读取的），同步到 textContent 方便查看
      if (parsed.text && sourceMode !== "text") {
        setTextContent(parsed.text);
      }
      // 为每个角色初始化默认配置
      const configs: Record<string, RoleConfig> = {};
      (parsed.roles || []).forEach((role: string, idx: number) => {
        configs[role] = roleConfigs[role] || {
          voice_id: voices.length > 0 ? voices[idx % voices.length].voice_id : "",
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

  const updateRoleConfig = (role: string, field: keyof RoleConfig, value: string | number) => {
    setRoleConfigs((prev) => ({
      ...prev,
      [role]: { ...prev[role], [field]: value },
    }));
  };

  const getRoleColor = (role: string) => {
    const idx = roles.indexOf(role);
    return ROLE_COLORS[idx % ROLE_COLORS.length];
  };

  // --- 提交任务 ---
  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (isMultiRole) {
        // 多角色对话模式 — 解析后 textContent 已同步文件内容
        if (!textContent.trim()) {
          alert("请先通过任意输入方式提供对话文本");
          setSubmitting(false);
          return;
        }
        if (segments.length === 0) {
          alert("请先点击「解析角色」按钮解析对话内容");
          setSubmitting(false);
          return;
        }
        const missingVoice = roles.find((r) => !roleConfigs[r]?.voice_id);
        if (missingVoice) {
          alert(`角色「${missingVoice}」尚未配置音色`);
          setSubmitting(false);
          return;
        }
        const roleVoices: Record<string, RoleConfig> = {};
        roles.forEach((r) => { roleVoices[r] = roleConfigs[r]; });
        await apiClient.post("/tts/dialogue", {
          text: textContent.trim(),
          role_voices: roleVoices,
          silence_gap: silenceGap,
          output_format: outputFormat,
          filename: taskName || undefined,
        });
      } else {
        // 单角色模式 — 通过 convert-from-file 统一接口
        const formData = new FormData();
        formData.append("voice_id", selectedVoice);
        formData.append("rate", rate.toString());
        formData.append("pitch", pitch);
        formData.append("volume", volume);
        formData.append("output_format", outputFormat);
        if (taskName) formData.append("filename", taskName);

        if (sourceMode === "select") {
          if (!sourceFileId) { alert("请选择源文件"); setSubmitting(false); return; }
          formData.append("file_id", sourceFileId);
        } else if (sourceMode === "text") {
          if (!textContent.trim()) { alert("请输入文字内容"); setSubmitting(false); return; }
          formData.append("text", textContent.trim());
        } else if (sourceMode === "manual") {
          if (!manualPath.trim()) { alert("请输入 GCS 路径"); setSubmitting(false); return; }
          formData.append("gcs_path", manualPath.trim());
        } else {
          alert("请先上传文件"); setSubmitting(false); return;
        }

        await apiClient.post("/tts/convert-from-file", formData);
      }
      loadTasks();
    } catch (error) {
      console.error("提交失败:", error);
      alert("提交任务失败");
    } finally {
      setSubmitting(false);
    }
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

        {/* 第一：统计卡片 */}
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

        {/* 第二：源文件输入 */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          {/* 四个 tab */}
          <div className="flex gap-2 mb-4">
            {([
              ["select", "📂 选择已有文件"],
              ["upload", "📤 本地上传"],
              ["text", "✍️ 手动输入文字"],
              ["manual", "🔗 手动输入路径"],
            ] as const).map(([m, label]) => (
              <button
                key={m}
                onClick={() => setSourceMode(m)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  sourceMode === m
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* tab 内容 */}
          {sourceMode === "select" && (
            <div>
              {/* 文件选择下拉框 */}
              <div className="relative" ref={fileDropdownRef}>
                <div
                  className="w-full p-3 border rounded-lg cursor-pointer flex items-center justify-between hover:border-indigo-400"
                  onClick={() => setFileDropdownOpen(!fileDropdownOpen)}
                >
                  <span className={sourceFilePath ? "text-gray-900" : "text-gray-400"}>
                    {sourceFilePath
                      ? gcsFiles.find((f) => f.file_id === sourceFileId)?.display_name || sourceFilePath
                      : `请选择源文件（共 ${totalFiles} 个）`}
                  </span>
                  <span className="text-gray-400">{fileDropdownOpen ? "▲" : "▼"}</span>
                </div>

                {fileDropdownOpen && (
                  <div className="absolute z-50 w-full mt-1 bg-white border rounded-xl shadow-lg max-h-80 overflow-hidden">
                    {/* 搜索 + 排序 */}
                    <div className="p-3 border-b flex gap-2">
                      <input
                        type="text"
                        value={fileSearch}
                        onChange={(e) => setFileSearch(e.target.value)}
                        placeholder="搜索文件名..."
                        className="flex-1 px-3 py-1.5 border rounded-lg text-sm"
                      />
                      <select
                        value={fileSortBy}
                        onChange={(e) => setFileSortBy(e.target.value as "name" | "time")}
                        className="px-2 py-1.5 border rounded-lg text-sm"
                      >
                        <option value="time">按时间</option>
                        <option value="name">按名称</option>
                      </select>
                    </div>
                    {/* 文件列表 */}
                    <div className="max-h-56 overflow-y-auto">
                      {filteredFiles.length === 0 ? (
                        <div className="p-4 text-center text-gray-400 text-sm">暂无文件</div>
                      ) : (
                        filteredFiles.map((f) => (
                          <div
                            key={f.file_id}
                            className={`px-4 py-3 cursor-pointer hover:bg-indigo-50 flex items-center justify-between ${
                              sourceFileId === f.file_id ? "bg-indigo-50" : ""
                            }`}
                          >
                            <div
                              className="flex-1"
                              onClick={() => {
                                setSourceFileId(f.file_id);
                                setSourceFilePath(f.gcs_path);
                                setFileDropdownOpen(false);
                              }}
                            >
                              <div className="font-medium text-sm">
                                📄 {f.display_name || f.original_filename}
                              </div>
                              <div className="text-xs text-gray-400 mt-0.5">
                                {f.file_extension} | {formatFileSize(f.file_size)} | {new Date(f.uploaded_at).toLocaleString("zh-CN")}
                              </div>
                            </div>
                            {/* 重命名按钮 */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setRenamingFileId(f.file_id);
                                setNewDisplayName(f.display_name || "");
                              }}
                              className="ml-2 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                            >
                              重命名
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* 重命名弹窗 */}
              {renamingFileId && (
                <div className="mt-3 flex items-center gap-2 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <span className="text-sm">新名称:</span>
                  <input
                    type="text"
                    value={newDisplayName}
                    onChange={(e) => setNewDisplayName(e.target.value)}
                    className="flex-1 px-2 py-1 border rounded text-sm"
                    onKeyDown={(e) => { if (e.key === "Enter") handleRename(renamingFileId); }}
                  />
                  <button
                    onClick={() => handleRename(renamingFileId)}
                    className="px-3 py-1 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
                  >
                    确认
                  </button>
                  <button
                    onClick={() => { setRenamingFileId(null); setNewDisplayName(""); }}
                    className="px-3 py-1 bg-gray-200 text-gray-600 rounded text-sm hover:bg-gray-300"
                  >
                    取消
                  </button>
                </div>
              )}
            </div>
          )}

          {sourceMode === "upload" && (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
                >
                  选择文件
                </button>
                <span className="text-sm text-gray-500">
                  {selectedFile ? selectedFile.name : "支持 .docx / .doc / .txt"}
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".txt,.doc,.docx"
                  onChange={handleLocalFileSelect}
                />
              </div>
              {selectedFile && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium whitespace-nowrap">显示名称:</label>
                    <input
                      type="text"
                      value={fileDisplayName}
                      onChange={(e) => setFileDisplayName(e.target.value)}
                      placeholder="输入文件显示名称"
                      className="flex-1 px-3 py-1.5 border rounded-lg text-sm"
                    />
                  </div>
                  <button
                    onClick={handleUploadToGcs}
                    disabled={uploading}
                    className="px-6 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-green-700"
                  >
                    {uploading ? `上传中 ${uploadProgress}%` : "📤 上传到云端"}
                  </button>
                  {uploading && (
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {sourceMode === "text" && (
            <div>
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder={
                  isMultiRole
                    ? "小明: 你好，今天天气真好\n小红: 是啊，我们去公园吧\n旁白: 于是他们一起出发了"
                    : "请输入需要转换为语音的文字内容..."
                }
                rows={8}
                className="w-full p-4 border rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
              />
              {isMultiRole && (
                <p className="text-sm text-gray-500 mt-2">
                  格式：每行 <code className="bg-gray-100 px-1 rounded">角色名: 对话内容</code>，无角色前缀视为旁白
                </p>
              )}
            </div>
          )}

          {sourceMode === "manual" && (
            <div>
              <input
                type="text"
                value={manualPath}
                onChange={(e) => setManualPath(e.target.value)}
                placeholder="gs://bucket-name/path/to/file.txt"
                className="w-full px-4 py-3 border rounded-lg text-sm font-mono focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
              />
              <p className="text-xs text-gray-400 mt-2">输入 GCS 完整路径，如 gs://vigloo-fission-uploads/vigloo-tts-uploads/files/source/xxx.txt</p>
            </div>
          )}

          {/* 多角色模式：解析按钮（适用于所有输入方式） */}
          {isMultiRole && (
            <div className="mt-4 pt-4 border-t flex items-center gap-3">
              <button
                onClick={() => handleParse()}
                disabled={parsing}
                className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-indigo-700 transition-colors"
              >
                {parsing ? "解析中..." : "🔍 解析角色"}
              </button>
              <span className="text-sm text-gray-500">
                {sourceMode === "text" && "解析输入的文字内容"}
                {sourceMode === "select" && "从已选文件中读取并解析"}
                {sourceMode === "upload" && "请先上传文件，再选择已有文件解析"}
                {sourceMode === "manual" && "从 GCS 路径读取并解析"}
              </span>
              {segments.length > 0 && (
                <span className="text-sm text-green-600 font-medium">
                  ✅ 已解析 {segments.length} 段，{roles.length} 个角色
                </span>
              )}
            </div>
          )}
          <div className="flex items-center gap-6 pt-4 border-t mt-4">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-2">任务命名</label>
              <input
                type="text"
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                placeholder="输入任务名称（可选）"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
              />
            </div>
            <div className="flex items-center gap-3 pt-6">
              <span className="text-sm font-medium text-gray-700">多角色对话</span>
              <button
                onClick={() => {
                  setIsMultiRole(!isMultiRole);
                  if (isMultiRole) {
                    // 关闭多角色时清空解析结果
                    setSegments([]);
                    setRoles([]);
                    setRoleConfigs({});
                  }
                }}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${
                  isMultiRole ? "bg-indigo-600" : "bg-gray-300"
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                    isMultiRole ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
              <span className="text-xs text-gray-400">（含旁白）</span>
            </div>
            {/* 语言模式 */}
            <div className="flex items-center gap-3 pt-6">
              <span className="text-sm font-medium text-gray-700">语言模式</span>
              <div className="flex rounded-lg overflow-hidden border">
                <button
                  onClick={() => setLanguageMode("single")}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    languageMode === "single"
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  单语种
                </button>
                <button
                  onClick={() => setLanguageMode("multi")}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    languageMode === "multi"
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  多语种
                </button>
              </div>
              {languageMode === "single" && (
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className="px-2 py-1.5 border rounded-lg text-sm"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </div>

        {/* 第四：音色配置 */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2">🎤 音色配置</h2>

          {!isMultiRole ? (
            /* 单角色模式 */
            <div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-4">
                {/* 音色选择 + 试听 */}
                <div>
                  <label className="block text-sm font-medium mb-2">音色</label>
                  <div className="flex items-center gap-2">
                    <select
                      value={selectedVoice}
                      onChange={(e) => setSelectedVoice(e.target.value)}
                      className="flex-1 p-2 border rounded-lg"
                    >
                      <option value="">请选择</option>
                      {voices.map((v) => (
                        <option key={v.voice_id} value={v.voice_id}>
                          {v.name} {v.gender === "male" ? "♂" : "♀"}
                        </option>
                      ))}
                    </select>
                    <VoicePreviewButton voiceId={selectedVoice} />
                  </div>
                </div>
                {/* 语速 */}
                <div>
                  <label className="block text-sm font-medium mb-2">语速: {rate.toFixed(1)}x</label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">慢</span>
                    <input
                      type="range" min="0.5" max="2.0" step="0.1"
                      value={rate}
                      onChange={(e) => setRate(parseFloat(e.target.value))}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs text-gray-400">快</span>
                  </div>
                </div>
                {/* 音调/语气 */}
                <div>
                  <label className="block text-sm font-medium mb-2">音调/语气</label>
                  <select
                    value={pitch}
                    onChange={(e) => setPitch(e.target.value)}
                    className="w-full p-2 border rounded-lg"
                  >
                    <option value="-20Hz">很低</option>
                    <option value="-10Hz">偏低</option>
                    <option value="+0Hz">默认</option>
                    <option value="+10Hz">偏高</option>
                    <option value="+20Hz">很高</option>
                  </select>
                </div>
                {/* 音量/重音 */}
                <div>
                  <label className="block text-sm font-medium mb-2">音量/重音</label>
                  <select
                    value={volume}
                    onChange={(e) => setVolume(e.target.value)}
                    className="w-full p-2 border rounded-lg"
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
          ) : (
            /* 多角色模式：逐角色配置 */
            <div>
              {roles.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2 opacity-50">🎭</div>
                  <p>请先在上方输入对话文本并点击「解析角色」</p>
                </div>
              ) : (
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
                        {/* 音色 + 试听 */}
                        <div>
                          <label className="block text-xs font-medium mb-1">音色</label>
                          <div className="flex items-center gap-2">
                            <select
                              value={roleConfigs[role]?.voice_id || ""}
                              onChange={(e) => updateRoleConfig(role, "voice_id", e.target.value)}
                              className="flex-1 p-2 border rounded-lg bg-white text-sm"
                            >
                              <option value="">请选择</option>
                              {voices.map((v) => (
                                <option key={v.voice_id} value={v.voice_id}>
                                  {v.name} {v.gender === "male" ? "♂" : "♀"}
                                </option>
                              ))}
                            </select>
                            <VoicePreviewButton voiceId={roleConfigs[role]?.voice_id || ""} />
                          </div>
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
                        {/* 音调/语气 */}
                        <div>
                          <label className="block text-xs font-medium mb-1">音调/语气</label>
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
                        {/* 音量/重音 */}
                        <div>
                          <label className="block text-xs font-medium mb-1">音量/重音</label>
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
              )}
            </div>
          )}

          {/* 全局设置 + 提交 */}
          <div className="mt-6 pt-4 border-t flex items-end gap-6">
            {isMultiRole && (
              <div>
                <label className="block text-sm font-medium mb-1">
                  句间静音: {silenceGap}ms
                </label>
                <input
                  type="range" min="0" max="3000" step="100"
                  value={silenceGap}
                  onChange={(e) => setSilenceGap(parseInt(e.target.value))}
                  className="w-48 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-400 w-48">
                  <span>0ms</span><span>3000ms</span>
                </div>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium mb-1">输出格式</label>
              <select
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value)}
                className="w-32 p-2 border rounded-lg"
              >
                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
              </select>
            </div>
            {/* 综合试听按钮 */}
            <FullPreviewButton
              isMultiRole={isMultiRole}
              voiceId={selectedVoice}
              rate={rate}
              pitch={pitch}
              volume={volume}
              roleConfigs={roleConfigs}
              segments={segments}
              roles={roles}
              silenceGap={silenceGap}
              sourceMode={sourceMode}
              textContent={textContent}
              sourceFileId={sourceFileId}
              manualPath={manualPath}
            />
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-8 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-semibold disabled:opacity-50 hover:shadow-lg transition-all"
            >
              {submitting ? "提交中..." : "🚀 开始转换"}
            </button>
          </div>
        </div>

        {/* 第五：任务列表 */}
        <TTSTaskList tasks={tasks} expandedTask={expandedTask} setExpandedTask={setExpandedTask} />

      </div>
    </div>
  );
}
