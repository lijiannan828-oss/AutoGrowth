"use client";

import { useState, useEffect, useRef } from "react";
import apiClient from "@/lib/api-client";

// ---- 模块级：跨组件共享，保证同一时间只有一个试听在播放 ----
let previewAudio: HTMLAudioElement | null = null;
let previewStopCb: (() => void) | null = null;

function stopGlobalPreview() {
  if (previewAudio) {
    previewAudio.pause();
    previewAudio = null;
  }
  previewStopCb?.();
  previewStopCb = null;
}

// ---- 音色试听按钮（内联样式，放在音色选择框后面）----
export function VoicePreviewButton({ voiceId }: { voiceId: string }) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  // 当全局播放的不是当前音色时，自动重置状态
  useEffect(() => {
    if (!playing) return;
    const check = setInterval(() => {
      if (previewAudio === null) {
        setPlaying(false);
        setProgress(0);
        clearInterval(check);
      }
    }, 300);
    return () => clearInterval(check);
  }, [playing]);

  const stopPlayback = () => {
    if (previewAudio) {
      previewAudio.pause();
      previewAudio = null;
    }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
    previewStopCb?.();
    previewStopCb = null;
    setPlaying(false);
    setProgress(0);
  };

  const handleToggle = async () => {
    if (!voiceId) return;
    if (playing) { stopPlayback(); return; }
    // 停止其他试听
    stopGlobalPreview();

    setLoading(true);
    try {
      const res = await apiClient.get(`/tts/preview/${voiceId}`);
      const url = res.data.preview_url;
      if (!url) return;

      const audio = new Audio(url);
      audio.onended = () => stopPlayback();
      audio.onerror = () => stopPlayback();

      previewAudio = audio;
      previewStopCb = () => {
        setPlaying(false);
        setProgress(0);
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
      };

      await audio.play();
      setPlaying(true);
      setLoading(false);

      // 更新进度条
      timerRef.current = setInterval(() => {
        if (previewAudio && previewAudio.duration) {
          const maxDuration = Math.min(previewAudio.duration, 10);
          const pct = Math.min((previewAudio.currentTime / maxDuration) * 100, 100);
          setProgress(pct);
        }
      }, 100);

      // 最多试听 10 秒
      timeoutRef.current = setTimeout(() => stopPlayback(), 10000);
    } catch {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleToggle}
        disabled={!voiceId || loading}
        className={`shrink-0 w-7 h-7 flex items-center justify-center rounded-full text-white text-xs transition-all disabled:opacity-40 ${
          playing
            ? "bg-yellow-500 hover:bg-yellow-600"
            : "bg-green-500 hover:bg-green-600"
        }`}
        title={playing ? "暂停试听" : "试听音色"}
      >
        {loading ? (
          <span className="animate-spin">&#x23F3;</span>
        ) : playing ? "\u23F8" : "\u25B6"}
      </button>
      {playing && (
        <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden min-w-[40px] max-w-[80px]">
          <div
            className="h-full bg-gradient-to-r from-green-400 to-green-600 rounded-full transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </>
  );
}

// ---- 综合试听按钮（基于所有音色配置 + 用户文本）----

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

interface FullPreviewProps {
  isMultiRole: boolean;
  // 单角色
  voiceId: string;
  rate: number;
  pitch: string;
  volume: string;
  // 多角色
  roleConfigs: Record<string, RoleConfig>;
  segments: DialogueSegment[];
  roles: string[];
  silenceGap: number;
  // 文本来源
  sourceMode: string;
  textContent: string;
  sourceFileId: string;
  manualPath: string;
}

export function FullPreviewButton({
  isMultiRole, voiceId, rate, pitch, volume,
  roleConfigs, segments, roles, silenceGap,
  sourceMode, textContent, sourceFileId, manualPath,
}: FullPreviewProps) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (!playing) return;
    const check = setInterval(() => {
      if (previewAudio === null) {
        setPlaying(false);
        setProgress(0);
        clearInterval(check);
      }
    }, 300);
    return () => clearInterval(check);
  }, [playing]);

  const stopPlayback = () => {
    if (previewAudio) { previewAudio.pause(); previewAudio = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
    previewStopCb?.();
    previewStopCb = null;
    setPlaying(false);
    setProgress(0);
  };

  const handleToggle = async () => {
    if (playing) { stopPlayback(); return; }
    stopGlobalPreview();

    setLoading(true);
    try {
      let res;
      if (!isMultiRole) {
        const formData = new FormData();
        formData.append("voice_id", voiceId);
        formData.append("rate", rate.toString());
        formData.append("pitch", pitch);
        formData.append("volume", volume);
        if (sourceMode === "text") formData.append("text", textContent);
        else if (sourceMode === "select") formData.append("file_id", sourceFileId);
        else if (sourceMode === "manual") formData.append("gcs_path", manualPath);
        res = await apiClient.post("/tts/preview-custom", formData);
      } else {
        // 多角色：发送对话文本 + 各角色配置
        const roleVoices: Record<string, RoleConfig> = {};
        roles.forEach((r) => { if (roleConfigs[r]) roleVoices[r] = roleConfigs[r]; });
        res = await apiClient.post("/tts/preview-dialogue-custom", {
          text: textContent,
          role_voices: roleVoices,
          silence_gap: silenceGap,
        });
      }

      const url = res.data.preview_url;
      if (!url) { setLoading(false); return; }

      const audio = new Audio(url);
      audio.onended = () => stopPlayback();
      audio.onerror = () => stopPlayback();

      previewAudio = audio;
      previewStopCb = () => {
        setPlaying(false);
        setProgress(0);
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
      };

      await audio.play();
      setPlaying(true);
      setLoading(false);

      timerRef.current = setInterval(() => {
        if (previewAudio && previewAudio.duration) {
          const maxDur = Math.min(previewAudio.duration, 20);
          setProgress(Math.min((previewAudio.currentTime / maxDur) * 100, 100));
        }
      }, 100);

      // 最多 20 秒
      timeoutRef.current = setTimeout(() => stopPlayback(), 20000);
    } catch {
      setLoading(false);
    }
  };

  // 禁用条件
  const hasText = !!(textContent.trim() || sourceFileId || manualPath.trim());
  const disabled = loading || (
    !isMultiRole
      ? !voiceId || !hasText
      : segments.length === 0 || roles.some((r) => !roleConfigs[r]?.voice_id) || !textContent.trim()
  );

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={disabled}
      className={`w-32 p-2 border rounded-lg text-sm relative overflow-hidden transition-all disabled:opacity-40 ${
        playing
          ? "bg-yellow-500 border-yellow-500 text-white hover:bg-yellow-600"
          : loading
          ? "bg-gray-300 border-gray-300 text-gray-600"
          : "bg-emerald-500 border-emerald-500 text-white hover:bg-emerald-600"
      }`}
    >
      {loading ? "生成中..." : playing ? "⏸ 暂停" : "▶ 试听"}
      {playing && (
        <div
          className="absolute bottom-0 left-0 h-1 bg-white/50 transition-all duration-100"
          style={{ width: `${progress}%` }}
        />
      )}
    </button>
  );
}
