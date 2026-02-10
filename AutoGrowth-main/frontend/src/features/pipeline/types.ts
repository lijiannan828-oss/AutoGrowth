export interface GDriveProgram {
  name: string;
  path: string;
  gdrive_id: string;
  in_gcs: boolean;
  files_total?: number;
  files_in_gcs?: number;
  updated_at?: string;
  total_size_bytes?: number;
}

export interface PipelineFolder {
  name: string;
  id: string;
  mimeType?: string;
  itemCount?: number;
  totalSizeBytes?: number;
  files_total?: number;
  files_in_gcs?: number;
  children?: PipelineFolder[];
}

export interface PipelineRoot {
  label: string;
  folder_id: string;
}

export interface FolderBrowseNode {
  id: string;
  name: string;
  has_children: boolean;
  in_gcs: boolean;
}

export interface SelectedFolderNode {
  id: string;
  name: string;
  path: string;
  gcsPrefix: string;
  in_gcs?: boolean;
}

export interface TransferRequestPayload {
  drama_name: string;
  gdrive_path: string;
  include_folders: string[];
}

export interface TransferResponse {
  job_id?: string;
  status?: string;
  queued_at?: string;
}

export interface PipelineFileNode {
  name: string;
  path: string;
  is_directory: boolean;
  size_bytes?: number;
  updated_at?: string;
  language?: string;
  children?: PipelineFileNode[];
}

export interface DownloadLinkResponse {
  url: string;
  expires_at?: string;
}

export interface ZipDownloadResponse {
  task_id?: string;
  status?: string;
}

export interface NasDownloadRequest {
  drama_name?: string;
  files: string[];
  notes?: string;
}

export interface NasDownloadResponse {
  task_id?: string;
  status?: string;
}

export interface ManualProcessRequest {
  drama_name: string;
  file_paths: string[];
}

export interface ManualProcessResponse {
  job_id?: string;
  status?: string;
}

