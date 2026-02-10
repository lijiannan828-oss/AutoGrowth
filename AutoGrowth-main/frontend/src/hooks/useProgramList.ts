import { useCallback, useMemo } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";

import apiClient from "@/lib/api-client";
import type { ProgramInfo, ProgramListResponse } from "@/types/api";

const DEFAULT_PAGE_SIZE = 20;

export interface UseProgramListOptions {
  pageSize?: number;
  keyword?: string;
  enabled?: boolean;
}

export interface UseProgramListResult {
  programs: ProgramInfo[];
  total: number;
  pageSize: number;
  isLoading: boolean;
  isFetching: boolean;
  isFetchingNextPage: boolean;
  isError: boolean;
  error: Error | null;
  hasNextPage: boolean;
  loadMore: () => void;
  refetch: () => void;
}

const fetchProgramList = async (
  pageParam: number,
  pageSize: number,
  keyword?: string,
): Promise<ProgramListResponse> => {
  const { data } = await apiClient.get<ProgramListResponse>("/data/programs", {
    params: {
      page: pageParam,
      page_size: pageSize,  // Backend expects page_size, not pageSize
      keyword: keyword?.trim() || undefined,
    },
  });
  return data;
};

export const useProgramList = ({
  pageSize = DEFAULT_PAGE_SIZE,
  keyword,
  enabled = true,
}: UseProgramListOptions = {}): UseProgramListResult => {
  const query = useInfiniteQuery<ProgramListResponse, Error>({
    queryKey: ["program-list", pageSize, keyword],
    queryFn: ({ pageParam = 1 }) => fetchProgramList(pageParam as number, pageSize, keyword),
    enabled,
    getNextPageParam: (lastPage) => {
      if (!lastPage) return undefined;
      const { page, pageSize: responsePageSize, total } = lastPage;
      const effectivePageSize = responsePageSize ?? pageSize;
      if (page * effectivePageSize >= total) {
        return undefined;
      }
      return page + 1;
    },
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    initialPageParam: 1,
  });

  const programs = useMemo(
    () => query.data?.pages.flatMap((page) => page.items ?? []) ?? [],
    [query.data?.pages],
  );

  const total = query.data?.pages.at(0)?.total ?? 0;

  const { hasNextPage, fetchNextPage } = query;

  const loadMore = useCallback(() => {
    if (hasNextPage) {
      void fetchNextPage();
    }
  }, [hasNextPage, fetchNextPage]);

  return {
    programs,
    total,
    pageSize,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isFetchingNextPage: query.isFetchingNextPage,
    isError: query.isError,
    error: query.error ?? null,
    hasNextPage: Boolean(hasNextPage),
    loadMore,
    refetch: query.refetch,
  };
};

export default useProgramList;

