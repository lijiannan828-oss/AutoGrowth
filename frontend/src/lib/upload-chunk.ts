// 分片上传与断点续传工具函数
import apiClient from './api-client';

export interface ChunkUploadOptions {
  chunkSize?: number; // 默认 5MB
  onProgress?: (percent: number) => void;
}

export async function uploadFileInChunks(
  file: File,
  options: ChunkUploadOptions = {}
): Promise<void> {
  const chunkSize = options.chunkSize || 5 * 1024 * 1024;
  const totalChunks = Math.ceil(file.size / chunkSize);
  let uploadedChunks = 0;

  // TODO: 查询已上传片段，实现断点续传
  // const uploaded = await apiClient.get(`/subtitle/upload/status?file=${file.name}`);

  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize;
    const end = Math.min(file.size, start + chunkSize);
    const chunk = file.slice(start, end);

    const fd = new FormData();
    fd.append('file', chunk);
    fd.append('chunkIndex', i.toString());
    fd.append('totalChunks', totalChunks.toString());
    fd.append('fileName', file.name);

    await apiClient.post('/subtitle/upload-chunk', fd, {
      timeout: 120000,
      onUploadProgress: (e: any) => {
        if (options.onProgress) {
          const percent = Math.round(((uploadedChunks + e.loaded / chunk.size) / totalChunks) * 100);
          options.onProgress(percent);
        }
      },
    });
    uploadedChunks++;
  }

  // 合并片段
  await apiClient.post('/subtitle/merge-chunks', {
    fileName: file.name,
    totalChunks,
  });
}
