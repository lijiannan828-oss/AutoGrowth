"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchGDriveStatus } from "@/features/pipeline/api";
import type { GDriveProgram } from "@/features/pipeline/types";
import { useAuth } from "@/hooks/useAuth";

export interface PipelineStatusRow extends GDriveProgram {
  category: string;
  programCode: string;
}

export function usePipelineStatus() {
  const { user, loading } = useAuth();
  const query = useQuery({
    queryKey: ["pipeline", "gdrive-status"],
    queryFn: fetchGDriveStatus,
    staleTime: 60 * 1000,
    enabled: Boolean(!loading && user),
  });

  const rows: PipelineStatusRow[] = useMemo(() => {
    if (!query.data) return [];
    return query.data.map((program) => {
      const segments = program.path.split("/").filter(Boolean);
      const category = segments[0] ?? "Unknown";
      const programCode = program.name ?? segments[segments.length - 1] ?? "";
      return {
        ...program,
        category,
        programCode,
      };
    });
  }, [query.data]);

  return {
    ...query,
    rows,
  };
}

