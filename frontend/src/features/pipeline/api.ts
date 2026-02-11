import apiClient from "@/lib/api-client";
import type {
  DownloadLinkResponse,
  FolderBrowseNode,
  GDriveProgram,
  ManualProcessRequest,
  ManualProcessResponse,
  NasDownloadRequest,
  NasDownloadResponse,
  PipelineFileNode,
  PipelineRoot,
  TransferRequestPayload,
  TransferResponse,
  ZipDownloadResponse,
} from "./types";

export async function fetchGDriveStatus(): Promise<GDriveProgram[]> {
  const { data } = await apiClient.get<GDriveProgram[]>("/pipeline/gdrive-status");
  return data ?? [];
}

export async function fetchPipelineRoots(): Promise<PipelineRoot[]> {
  const { data } = await apiClient.get<PipelineRoot[]>("/pipeline/gdrive-roots");
  return data ?? [];
}

export async function fetchUnprocessedDramas(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>("/pipeline/unprocessed-dramas");
  return data ?? [];
}

export async function browseDriveFolder(params: {
  driveFolderId: string;
  gcsPrefix?: string;
}): Promise<FolderBrowseNode[]> {
  if (!params.driveFolderId) {
    return [];
  }
  const { data } = await apiClient.get<FolderBrowseNode[]>("/pipeline/gdrive-browse", {
    params: {
      drive_folder_id: params.driveFolderId,
      gcs_prefix: params.gcsPrefix,
    },
  });
  return data ?? [];
}

export async function createTransferJob(
  payload: TransferRequestPayload,
): Promise<TransferResponse> {
  const { data } = await apiClient.post<TransferResponse>("/pipeline/transfer", payload);
  return data ?? {};
}

export async function fetchPipelineFiles(params: {
  scope: "source" | "processed";
  drama?: string;
  search?: string;
}): Promise<PipelineFileNode[]> {
  const { data } = await apiClient.get<PipelineFileNode[]>("/pipeline/processed-files", {
    params: {
      type: params.scope,
      drama: params.drama,
      q: params.search,
    },
  });
  return data ?? [];
}

export async function fetchDownloadLink(filePath: string): Promise<DownloadLinkResponse> {
  const { data } = await apiClient.get<DownloadLinkResponse>("/pipeline/download-link", {
    params: { file_path: filePath },
  });
  return data ?? { url: "" };
}

export async function requestZipDownload(paths: string[]): Promise<ZipDownloadResponse> {
  const { data } = await apiClient.post<ZipDownloadResponse>("/pipeline/download-zip", {
    paths,
  });
  return data ?? {};
}

export interface ZipTaskStatus {
  task_id: string;
  status: string;
  status_message?: string;
  progress?: number;
  download_url?: string;
  speed_bps?: number;
  estimated_seconds?: number;
  downloaded_bytes?: number;
  total_bytes?: number;
  created_at?: string;
  updated_at?: string;
}

export async function getZipTaskStatus(taskId: string): Promise<ZipTaskStatus> {
  const { data } = await apiClient.get<ZipTaskStatus>(`/pipeline/zip-task/${taskId}`);
  return data ?? { task_id: taskId, status: "QUEUED" };
}

export async function requestNasDownload(
  payload: NasDownloadRequest,
): Promise<NasDownloadResponse> {
  const { data } = await apiClient.post<NasDownloadResponse>("/pipeline/download-to-nas", payload);
  return data ?? {};
}

export async function triggerManualProcess(
  payload: ManualProcessRequest,
): Promise<ManualProcessResponse> {
  const { data } = await apiClient.post<ManualProcessResponse>("/pipeline/process-manual", payload);
  return data ?? {};
}

export interface BatchDownloadItem {
  path: string;
  url: string;
  size: number;
}

export interface BatchDownloadResponse {
  files: BatchDownloadItem[];
  errors?: string[];
}

export async function fetchBatchDownloadUrls(paths: string[]): Promise<BatchDownloadResponse> {
  const { data } = await apiClient.post<BatchDownloadResponse>("/pipeline/batch-urls", {
    paths,
  });
  return data ?? { files: [] };
}
