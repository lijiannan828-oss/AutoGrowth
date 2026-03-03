"use client";

import { useState, useEffect, useRef } from "react";
import apiClient from "@/lib/api-client";

interface TTSTask {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  text: string;
  voice_id?: string;
  rate?: number;
  pitch?: string;
  volume?: string;
  output_format?: string;
  type?: string;
  roles?: string[];
  role_voices?: Record<string, { voice_id: string; rate: number; pitch: string; volume: string }>;
  segment_count?: number;
  audio_file?: string;
  filename?: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

interface TTSTaskListProps {
  tasks: TTSTask[];
  expandedTask: string | null;
  setExpandedTask: (id: string | null) => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const STATUS_LABELS: Record<string, string> = {
  completed: "✅ 已完成",
  processing: "⏳ 处理中",
  failed: "❌ 失败",
  pending: "🕐 等待处理",
};

function TaskCard({ task, isExpanded, onToggle }: { task: TTSTask; isExpanded: boolean; onToggle: () => void }) {
  return (
    <div className="border rounded-xl p-5">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold">
            {task.type === "dialogue" ? "🎭" : "🔊"}{" "}
            {task.filename || task.text}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {task.type === "dialogue"
              ? `${task.roles?.join("、")} | ${task.segment_count}段`
              : `音色: ${task.voice_id || "-"}`}
            {" | "}
            {new Date(task.created_at).toLocaleString("zh-CN")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[task.status] || "bg-gray-100 text-gray-800"}`}>
              {STATUS_LABELS[task.status] || task.status}
            </span>
            <p className="text-sm text-gray-500 mt-1">{task.progress}%</p>
          </div>
          <button
            onClick={onToggle}
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

      {isExpanded && (
        <div className="mt-4 border-t pt-4">
          <h4 className="font-medium mb-3">🎤 音色配置</h4>
          {task.type === "dialogue" && task.role_voices ? (
            <div className="space-y-2">
              {Object.entries(task.role_voices).map(([role, cfg]) => (
                <div key={role} className="flex flex-wrap gap-3 text-sm bg-gray-50 rounded-lg p-3">
                  <span className="font-medium">{role}:</span>
                  <span>音色 {cfg.voice_id}</span>
                  <span>语速 {cfg.rate}x</span>
                  <span>音调 {cfg.pitch}</span>
                  <span>音量 {cfg.volume}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-4 text-sm bg-gray-50 rounded-lg p-3">
              <span>音色: {task.voice_id || "-"}</span>
              <span>语速: {task.rate ?? 1.0}x</span>
              <span>音调: {task.pitch || "+0Hz"}</span>
              <span>音量: {task.volume || "+0%"}</span>
              <span>格式: {task.output_format || "mp3"}</span>
            </div>
          )}
        </div>
      )}

      {isExpanded && task.status === "completed" && task.audio_file && (
        <AudioActions taskId={task.audio_file} filename={task.filename || task.task_id} />
      )}
    </div>
  );
}

// 模块级：跨组件共享，切换任务时停止上一个
let globalAudio: HTMLAudioElement | null = null;
let globalStopCb: (() => void) | null = null;

function AudioActions({ taskId, filename }: { taskId: string; filename: string }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const stopProgress = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setProgress(0);
  };

  const startProgress = () => {
    timerRef.current = setInterval(() => {
      if (globalAudio && globalAudio.duration) {
        const pct = (globalAudio.currentTime / globalAudio.duration) * 100;
        setProgress(Math.min(pct, 100));
      }
    }, 200);
  };

  const handleToggle = async () => {
    if (playing) {
      globalAudio?.pause();
      setPlaying(false);
      stopProgress();
      return;
    }
    // 停止其他任务的播放
    if (globalAudio) { globalAudio.pause(); globalStopCb?.(); }
    try {
      const res = await apiClient.get(`/tts/download/${taskId}`);
      const url = res.data.download_url;
      if (!url) return;
      const audio = new Audio(url);
      audio.onended = () => { setPlaying(false); stopProgress(); globalAudio = null; };
      globalAudio = audio;
      globalStopCb = () => { setPlaying(false); stopProgress(); };
      await audio.play();
      setPlaying(true);
      startProgress();
    } catch { alert("播放失败"); }
  };

  const handleDownload = async () => {
    try {
      const res = await apiClient.get(`/tts/download/${taskId}`);
      if (res.data.download_url) {
        const a = document.createElement("a");
        a.href = res.data.download_url;
        a.download = `${filename}.mp3`;
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    } catch { alert("下载失败"); }
  };

  return (
    <div className="mt-4 border-t pt-4">
      <h4 className="font-medium mb-3">🎧 音频操作</h4>
      <div className="flex items-center gap-2">
        <button onClick={handleToggle} className={`shrink-0 text-xs text-white px-3 py-1 rounded-lg ${playing ? "bg-yellow-600 hover:bg-yellow-700" : "bg-green-600 hover:bg-green-700"}`}>
          {playing ? "⏸ 暂停" : "▶ 播放"}
        </button>
        {playing && (
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden min-w-[120px]">
            <div
              className="h-full bg-gradient-to-r from-green-400 to-green-600 rounded-full transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        <button onClick={handleDownload} className="shrink-0 text-xs bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700">
          📥 下载
        </button>
      </div>
    </div>
  );
}

export default function TTSTaskList({ tasks, expandedTask, setExpandedTask }: TTSTaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="bg-card rounded-xl border shadow-sm p-6">
        <h2 className="text-base font-semibold mb-4 pb-2 border-b">任务列表</h2>
        <div className="text-center py-16 text-muted-foreground">
          <h3 className="text-lg font-medium">暂无转换任务</h3>
          <p>上传文本文件或输入文字开始语音合成</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl border shadow-sm p-6">
      <h2 className="text-base font-semibold mb-4 pb-2 border-b">任务列表</h2>
      <div className="space-y-4">
        {tasks.map((task) => {
          const isExpanded = expandedTask === task.task_id;
          return (
            <TaskCard
              key={task.task_id}
              task={task}
              isExpanded={isExpanded}
              onToggle={() => setExpandedTask(isExpanded ? null : task.task_id)}
            />
          );
        })}
      </div>
    </div>
  );
}
