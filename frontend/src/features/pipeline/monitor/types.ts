export type PipelineStatus =
  | "QUEUED"
  | "TRANSFERRING"
  | "PROCESSING"
  | "COMPLETE"
  | "FAILED"
  | "FAILED_STAGE2"
  | "RETRYING"
  | "UNKNOWN";

export interface FailureDetail {
  stage: "transfer" | "process";
  file_path?: string | null;
  error_message?: string | null;
}

export interface TransferStatus {
  status?: string | null;
  progress_text?: string | null;
}

export interface ProcessStatus {
  status?: string | null;
  progress_text?: string | null;
  processed_count?: number | null;
  total_count?: number | null;
  language_details?: Record<string, { total?: number | null; done?: number | null }>;
}

export interface PipelineJobDoc {
  id: string;
  drama_name: string;
  job_type?: string | null;
  source_path?: string | null;
  status?: string | null;
  stats?: {
    files_total?: number | null;
    files_done?: number | null;
    speed_bps?: number | null;
  };
  transfer: TransferStatus;
  process: ProcessStatus;
  failures: FailureDetail[];
  last_updated?: string;
}

export type MonitorBucketKey =
  | "transferring"
  | "processing"
  | "completed"
  | "transferFailed"
  | "compressionFailed";

export interface MonitorBucket {
  key: MonitorBucketKey;
  title: string;
  description: string;
  data: PipelineJobDoc[];
}


