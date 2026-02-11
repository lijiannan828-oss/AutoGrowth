"use client";

import { useCallback, useEffect, useState } from "react";
import apiClient from "@/lib/api-client";
import type {
  FailureDetail,
  PipelineJobDoc,
  ProcessStatus,
  TransferStatus,
} from "./types";

interface PipelineJobApiItem {
  job_id: string;
  drama_name: string;
  job_type?: string | null;
  source_path?: string | null;
  status?: string | null;
  stats?: {
    files_total?: number | null;
    files_done?: number | null;
    speed_bps?: number | null;
  };
  transfer?: TransferStatus;
  process?: ProcessStatus;
  failures?: FailureDetail[];
  last_updated?: string | null;
}

interface PipelineJobsResponse {
  items: PipelineJobApiItem[];
}

const normalizeIso = (value?: string | null): string | undefined => {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }
  return date.toISOString();
};

export function usePipelineJobs(pollInterval = 15_000) {
  const [jobs, setJobs] = useState<PipelineJobDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const fetchJobs = useCallback(async () => {
    try {
      const response = await apiClient.get<PipelineJobsResponse>("/pipeline/jobs");
      const items = response.data?.items ?? [];
      const normalized: PipelineJobDoc[] = items.map((item) => ({
        id: item.job_id,
        drama_name: item.drama_name,
        job_type: item.job_type,
        source_path: item.source_path,
        status: item.status,
        stats: item.stats,
        transfer: item.transfer ?? {},
        process: item.process ?? {},
        failures: item.failures ?? [],
        last_updated: normalizeIso(item.last_updated as string | undefined),
      }));
      setJobs(normalized);
      setError(undefined);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "获取任务列表失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      if (!mounted) return;
      await fetchJobs();
    };

    load();

    const timer = setInterval(() => {
      load();
    }, pollInterval);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [fetchJobs, pollInterval]);

  return { jobs, loading, error, reload: fetchJobs };
}

