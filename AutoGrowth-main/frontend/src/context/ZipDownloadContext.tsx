"use client";

import { createContext, useContext, useState, ReactNode, useCallback, useRef } from "react";
import { message } from "antd";
import { fetchBatchDownloadUrls, BatchDownloadItem } from "@/features/pipeline/api";
import { apiClient } from "@/lib/api-client";

// File System Access API Types
interface FileSystemHandle {
  kind: "file" | "directory";
  name: string;
}

interface FileSystemDirectoryHandle extends FileSystemHandle {
  kind: "directory";
  getDirectoryHandle(name: string, options?: { create?: boolean }): Promise<FileSystemDirectoryHandle>;
  getFileHandle(name: string, options?: { create?: boolean }): Promise<FileSystemFileHandle>;
}

interface FileSystemFileHandle extends FileSystemHandle {
  kind: "file";
  createWritable(): Promise<FileSystemWritableFileStream>;
}

interface FileSystemWritableFileStream extends WritableStream {
  write(data: any): Promise<void>;
  close(): Promise<void>;
}

declare global {
  interface Window {
    showDirectoryPicker(): Promise<FileSystemDirectoryHandle>;
  }
}

interface ZipTask {
  taskId: string;
  status: "QUEUED" | "PROCESSING" | "COMPLETE" | "FAILED";
  statusMessage: string;
  zipUrl: string | null;
  progress: number; // 0-100
  speedBps?: number; // bytes per second
  estimatedSeconds?: number; // estimated remaining seconds
  downloadedBytes?: number;
  totalBytes?: number;
  createdAt: number;
}

interface ZipDownloadContextType {
  tasks: ZipTask[];
  activeTaskCount: number;
  latestTask: ZipTask | null;
  isVisible: boolean;
  isMinimized: boolean;
  startDownload: (paths: string[], bucket?: string) => Promise<void>;
  closeCard: () => void;
  minimizeCard: () => void;
}

const ZipDownloadContext = createContext<ZipDownloadContextType | null>(null);

export function ZipDownloadProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<ZipTask[]>([]);
  const [isVisible, setIsVisible] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  // Ref to track active downloads for cancellation or updates (not fully implemented yet)
  const activeDownloads = useRef<Set<string>>(new Set());

  const updateTask = useCallback((taskId: string, updates: Partial<ZipTask>) => {
    setTasks(prev => prev.map(t => t.taskId === taskId ? { ...t, ...updates } : t));
  }, []);

  const startDownload = useCallback(async (paths: string[], bucket?: string) => {
    console.log("[startDownload] 函数被调用，paths:", paths, "bucket:", bucket);
    if (paths.length === 0) {
      console.warn("[startDownload] paths为空，返回");
      return;
    }
    
    // 从 paths 中提取 bucket（如果 paths 是 gs:// 格式）
    let detectedBucket = bucket;
    if (!detectedBucket && paths.length > 0 && paths[0]?.startsWith('gs://')) {
      const match = paths[0].match(/^gs:\/\/([^\/]+)\//);
      detectedBucket = match ? match[1] : 'vigloo_processed';
    }
    detectedBucket = detectedBucket || 'vigloo_processed';
    console.log("[startDownload] 使用的 bucket:", detectedBucket);

    // 1. Check browser support
    console.log("[startDownload] 检查浏览器支持，showDirectoryPicker in window:", 'showDirectoryPicker' in window);
    if (!('showDirectoryPicker' in window)) {
      console.error("[startDownload] 浏览器不支持 showDirectoryPicker");
      message.error("您的浏览器不支持文件夹直写功能，请使用 Chrome 或 Edge");
      return;
    }

    const taskId = `local-${Date.now()}`;
    console.log("[startDownload] taskId:", taskId);

    try {
      // 1. Request directory access from user FIRST (must be in user gesture context)
      console.log("[startDownload] 准备弹出文件夹选择器...");
      let dirHandle: FileSystemDirectoryHandle;
      try {
        console.log("[startDownload] 调用 window.showDirectoryPicker()...");
        dirHandle = await window.showDirectoryPicker();
        console.log("[startDownload] 用户已选择文件夹:", dirHandle.name);
      } catch (err) {
        console.error("[startDownload] 文件夹选择器错误:", err);
        console.error("[startDownload] 错误类型:", (err as Error).constructor.name);
        console.error("[startDownload] 错误名称:", (err as Error).name);
        console.error("[startDownload] 错误消息:", (err as Error).message);
        if ((err as Error).name === 'AbortError') {
          console.log("[startDownload] 用户取消了文件夹选择");
          return; // User cancelled
        }
        message.error(`文件夹选择失败: ${err instanceof Error ? err.message : String(err)}`);
        throw err;
      }

      // 2. Get file list and signed URLs from backend (after folder selection)
      const loadingMsg = message.loading("正在获取文件列表...", 0);
      let batchResponse;
      try {
        console.log("[Download] 开始获取文件列表，路径:", paths);
        console.log("[Download] API baseURL:", apiClient.defaults.baseURL);
        console.log("[Download] 请求 payload:", JSON.stringify({ paths }, null, 2));
        
        batchResponse = await fetchBatchDownloadUrls(paths);
        
        console.log("[Download] 获取文件列表成功，响应:", batchResponse);
        console.log("[Download] 文件数量:", batchResponse.files?.length);
        
        if (batchResponse.errors && batchResponse.errors.length > 0) {
          console.warn("[Download] 后端返回的错误信息:", batchResponse.errors);
          message.warning(`部分路径处理失败: ${batchResponse.errors.join("; ")}`);
        }
        
        if (batchResponse.files && batchResponse.files.length > 0) {
          console.log("[Download] 前3个文件示例:", batchResponse.files.slice(0, 3).map(f => ({
            path: f.path,
            size: f.size,
            url: f.url.substring(0, 100) + "..."
          })));
        }
      } catch (err) {
        loadingMsg();
        console.error("[Download] 获取文件列表失败:", err);
        console.error("[Download] 错误详情:", {
          message: err instanceof Error ? err.message : String(err),
          stack: err instanceof Error ? err.stack : undefined,
          response: (err as any)?.response?.data,
          status: (err as any)?.response?.status,
        });
        message.error(`获取文件列表失败: ${err instanceof Error ? err.message : String(err)}`);
        return;
      } finally {
        loadingMsg();
      }

      if (!batchResponse?.files || batchResponse.files.length === 0) {
        console.warn("[Download] 未找到可下载的文件");
        console.warn("[Download] 响应内容:", JSON.stringify(batchResponse, null, 2));
        message.warning("未找到可下载的文件，请检查路径是否正确");
        return;
      }

      // 4. Initialize task
      setIsVisible(true);
      setIsMinimized(false);
      activeDownloads.current.add(taskId);

      const totalBytes = batchResponse.files.reduce((acc, f) => acc + f.size, 0);
      const totalFiles = batchResponse.files.length;

      const newTask: ZipTask = {
        taskId,
        status: "PROCESSING",
        statusMessage: "准备开始下载...",
        zipUrl: null,
        progress: 0,
        totalBytes,
        downloadedBytes: 0,
        createdAt: Date.now(),
      };
      setTasks(prev => [...prev, newTask]);

      // 5. Start concurrent download
      let completedFiles = 0;
      let downloadedBytes = 0;
      let failedFiles = 0;
      const startTime = Date.now();
      const CONCURRENCY = 5; // Max parallel downloads

      // Helper to get nested directory handle
      const getDirHandle = async (root: FileSystemDirectoryHandle, path: string) => {
        const parts = path.split('/').filter(p => p);
        let current = root;
        // If the path is just a filename, return root
        if (parts.length <= 1) return root;

        // Iterate up to the last part (filename)
        for (let i = 0; i < parts.length - 1; i++) {
          const dirName = parts[i];
          try {
            current = await current.getDirectoryHandle(dirName, { create: true });
            console.log(`[Download] 创建/获取目录: ${dirName}`);
          } catch (dirErr) {
            console.error(`[Download] 创建目录失败: ${dirName}`, dirErr);
            throw new Error(`无法创建目录 "${dirName}": ${dirErr instanceof Error ? dirErr.message : String(dirErr)}`);
          }
        }
        return current;
      };

      // Helper to download single file
      const downloadFile = async (file: BatchDownloadItem): Promise<{ success: boolean; bytes: number; error?: string }> => {
        try {
          console.log(`[Download] 开始下载文件: ${file.path}, URL: ${file.url.substring(0, 100)}...`);
          
          // file.path 是完整的 GCS 路径，例如: "KR051P07S01_김대표의 엽기적인 부인/ar_translated/ep001.mp4"
          // 需要保持这个目录结构
          let dir: FileSystemDirectoryHandle;
          try {
            dir = await getDirHandle(dirHandle, file.path);
            console.log(`[Download] 目录创建成功: ${file.path}`);
          } catch (dirErr) {
            const errorMsg = `目录创建失败: ${dirErr instanceof Error ? dirErr.message : String(dirErr)}`;
            console.error(`[Download] ${errorMsg}`, dirErr);
            return { success: false, bytes: 0, error: errorMsg };
          }

          const filename = file.path.split('/').pop()!;
          let fileHandle: FileSystemFileHandle;
          try {
            fileHandle = await dir.getFileHandle(filename, { create: true });
            console.log(`[Download] 文件句柄创建成功: ${filename}`);
          } catch (fileErr) {
            const errorMsg = `文件句柄创建失败: ${fileErr instanceof Error ? fileErr.message : String(fileErr)}`;
            console.error(`[Download] ${errorMsg}`, fileErr);
            return { success: false, bytes: 0, error: errorMsg };
          }

          let writable: FileSystemWritableFileStream;
          try {
            writable = await fileHandle.createWritable();
            console.log(`[Download] 可写流创建成功: ${filename}`);
          } catch (writeErr) {
            const errorMsg = `可写流创建失败: ${writeErr instanceof Error ? writeErr.message : String(writeErr)}`;
            console.error(`[Download] ${errorMsg}`, writeErr);
            return { success: false, bytes: 0, error: errorMsg };
          }

          let response: Response | undefined;
          try {
            // 使用后端代理端点避免 CORS 问题
            // file.path 格式: "KR065P01S01_죽여야하는,로맨스/en/ep000.mp4"
            // 需要转换为 gs://bucket/path 格式
            const gcsPath = `gs://${detectedBucket}/${file.path}`;
            
            // 生产环境优先直连签名 URL（需已配置 GCS CORS）；失败则回退代理
            const isProdDomain = typeof window !== 'undefined' && window.location.origin === 'https://autogrowth-477909.web.app';
            const apiBaseUrl = apiClient.defaults.baseURL || 'http://localhost:8000/api';
            const proxyUrl = `${apiBaseUrl}/pipeline/download-proxy?file_path=${encodeURIComponent(gcsPath)}`;
            const directUrl = file.url;
            
            console.log(`[Download] apiClient baseURL: ${apiClient.defaults.baseURL}`);
            console.log(`[Download] 检测到的 bucket: ${detectedBucket}`);
            console.log(`[Download] file.path: ${file.path}`);
            console.log(`[Download] GCS路径: ${gcsPath}`);
            console.log(`[Download] 直连候选: ${isProdDomain ? '是' : '否'} -> ${directUrl?.slice(0, 120)}...`);
            
            // 获取认证 token（仅代理请求需要）
            const token = typeof window !== 'undefined' ? window.localStorage.getItem('autogrowth.idToken') : null;
            const proxyHeaders: HeadersInit = {};
            if (token) {
              proxyHeaders['Authorization'] = `Bearer ${token}`;
              console.log(`[Download] 已添加认证 token (长度: ${token.length})`);
            } else {
              console.warn(`[Download] 未找到认证 token`);
            }
            
            // 尝试直连（生产环境），失败则切换到代理
            let usedDirect = false;
            if (isProdDomain && directUrl) {
              try {
                console.log(`[Download] 尝试直连签名 URL`);
                const directResp = await fetch(directUrl, { credentials: 'omit' });
                if (directResp.ok && directResp.body) {
                  response = directResp;
                  usedDirect = true;
                } else {
                  console.warn(`[Download] 直连失败，状态: ${directResp.status} ${directResp.statusText}，切换代理`);
                }
              } catch (e) {
                console.warn(`[Download] 直连异常，切换代理:`, e);
              }
            }
            
            if (!usedDirect) {
              console.log(`[Download] 使用代理下载: ${proxyUrl}`);
              response = await fetch(proxyUrl, {
                headers: proxyHeaders,
                credentials: 'include',
              });
            }
            if (!response) {
              const errorMsg = "未能获取到下载响应（直连与代理均失败）";
              console.error(`[Download] ${errorMsg}`);
              await writable.close();
              return { success: false, bytes: 0, error: errorMsg };
            }
            console.log(`[Download] Fetch 响应状态: ${response.status} ${response.statusText}`);
            console.log(`[Download] Fetch 响应 URL: ${response.url}`);
            
            if (!response.ok) {
              const errorMsg = `HTTP ${response.status}: ${response.statusText}`;
              console.error(`[Download] ${errorMsg}`);
              await writable.close();
              return { success: false, bytes: 0, error: errorMsg };
            }
            
            if (!response.body) {
              const errorMsg = "响应体为空";
              console.error(`[Download] ${errorMsg}`);
              await writable.close();
              return { success: false, bytes: 0, error: errorMsg };
            }
          } catch (fetchErr) {
            const errorMsg = `网络请求失败: ${fetchErr instanceof Error ? fetchErr.message : String(fetchErr)}`;
            console.error(`[Download] ${errorMsg}`, fetchErr);
            try {
              await writable.close();
            } catch (closeErr) {
              console.error(`[Download] 关闭可写流失败:`, closeErr);
            }
            return { success: false, bytes: 0, error: errorMsg };
          }

          try {
            console.log(`[Download] 开始写入文件: ${filename}`);
            console.log(`[Download] response.body 类型: ${response.body?.constructor?.name}`);
            console.log(`[Download] writable 类型: ${writable?.constructor?.name}`);
            
            // pipeTo 会自动关闭 writable 流，不需要手动关闭
            await response.body.pipeTo(writable);
            
            console.log(`[Download] pipeTo 完成: ${filename}`);
            
            return { success: true, bytes: file.size };
          } catch (pipeErr) {
            const errorMsg = `流式写入失败: ${pipeErr instanceof Error ? pipeErr.message : String(pipeErr)}`;
            console.error(`[Download] ${errorMsg}`, pipeErr);
            // pipeTo 失败时，writable 可能已经关闭，尝试关闭但忽略错误
            try {
              await writable.close();
            } catch (closeErr) {
              // 忽略关闭错误，因为流可能已经关闭
              console.warn(`[Download] 关闭可写流时出错（可忽略）:`, closeErr);
            }
            return { success: false, bytes: 0, error: errorMsg };
          }
        } catch (err) {
          const errorMsg = `未知错误: ${err instanceof Error ? err.message : String(err)}`;
          console.error(`[Download] Failed to download ${file.path}:`, err);
          return { success: false, bytes: 0, error: errorMsg };
        }
      };

      // Simple concurrency queue with progress updates
      const queue = [...batchResponse.files];
      const failedFileDetails: Array<{ path: string; error: string }> = [];
      const workers = Array(Math.min(queue.length, CONCURRENCY)).fill(null).map(async () => {
        while (queue.length > 0) {
          const file = queue.shift();
          if (file) {
            const result = await downloadFile(file);
            
            // Update counters atomically
            if (result.success) {
              completedFiles++;
              downloadedBytes += result.bytes;
            } else {
              failedFiles++;
              failedFileDetails.push({ path: file.path, error: result.error || "未知错误" });
              console.error(`[Download] 文件下载失败: ${file.path}, 错误: ${result.error || "未知错误"}`);
            }

            // Update progress
            const now = Date.now();
            const elapsedSeconds = (now - startTime) / 1000;
            const speedBps = elapsedSeconds > 0 ? downloadedBytes / elapsedSeconds : 0;
            const remainingBytes = totalBytes - downloadedBytes;
            const estimatedSeconds = speedBps > 0 ? remainingBytes / speedBps : 0;
            const progress = Math.min(Math.round((completedFiles / totalFiles) * 100), 99);

            // 显示当前下载的文件名（如果有）
            const currentFile = queue.length > 0 ? queue[0]?.path.split('/').pop() : undefined;
            const fileInfo = currentFile ? `: ${currentFile}` : '';
            const failedInfo = failedFiles > 0 ? ` (失败: ${failedFiles})` : '';
            const speedInfo = speedBps > 0 ? ` (${(speedBps / 1024 / 1024).toFixed(1)} MB/s)` : '';
            updateTask(taskId, {
              statusMessage: `正在下载 (${completedFiles}/${totalFiles})${failedInfo}${fileInfo}${speedInfo}`,
              progress,
              downloadedBytes,
              speedBps,
              estimatedSeconds
            });
          }
        }
      });

      await Promise.all(workers);

      // 6. Complete
      updateTask(taskId, {
        status: "COMPLETE",
        statusMessage: failedFiles > 0 
          ? `下载完成 (失败: ${failedFiles}/${totalFiles})` 
          : `下载完成 (${completedFiles}/${totalFiles})`,
        progress: 100,
        estimatedSeconds: 0
      });

      if (failedFiles > 0) {
        const errorSummary = failedFileDetails.slice(0, 5).map(f => `  - ${f.path}: ${f.error}`).join('\n');
        const moreErrors = failedFileDetails.length > 5 ? `\n  ... 还有 ${failedFileDetails.length - 5} 个错误` : '';
        console.error(`[Download] 下载完成，但有 ${failedFiles} 个文件失败:\n${errorSummary}${moreErrors}`);
        message.warning(`下载完成，但有 ${failedFiles} 个文件失败。请查看控制台了解详情。`);
      } else {
        message.success("所有文件下载完成");
      }

    } catch (err) {
      console.error(err);
      message.error("下载任务失败");
      updateTask(taskId, {
        status: "FAILED",
        statusMessage: "下载失败: " + (err as Error).message,
      });
    } finally {
      activeDownloads.current.delete(taskId);
    }
  }, [updateTask]);

  const closeCard = useCallback(() => {
    setIsVisible(false);
  }, []);

  const minimizeCard = useCallback(() => {
    setIsMinimized(prev => !prev);
  }, []);

  // 计算活跃任务数和最新任务
  const activeTaskCount = tasks.filter(t => t.status !== "COMPLETE" && t.status !== "FAILED").length;
  const latestTask = tasks.length > 0
    ? tasks.reduce((latest, current) => current.createdAt > latest.createdAt ? current : latest)
    : null;

  return (
    <ZipDownloadContext.Provider
      value={{
        tasks,
        activeTaskCount,
        latestTask,
        isVisible,
        isMinimized,
        startDownload,
        closeCard,
        minimizeCard,
      }}
    >
      {children}
    </ZipDownloadContext.Provider>
  );
}

export function useZipDownload() {
  const context = useContext(ZipDownloadContext);
  if (!context) {
    throw new Error("useZipDownload must be used within a ZipDownloadProvider");
  }
  return context;
}

