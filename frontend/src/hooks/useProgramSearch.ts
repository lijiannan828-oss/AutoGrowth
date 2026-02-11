import { useEffect, useMemo, useState } from "react";
import { useQuery, UseQueryResult } from "@tanstack/react-query";

import apiClient from "@/lib/api-client";
import type { ProgramInfo, ProgramListResponse } from "@/types/api";

const DEFAULT_PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 300;

type ProgramSearchQueryResult = UseQueryResult<ProgramInfo[], Error>;

const fetchPrograms = async (keyword: string): Promise<ProgramInfo[]> => {
  const trimmedKeyword = keyword.trim();
  if (!trimmedKeyword) {
    return [];
  }

  const { data } = await apiClient.get<ProgramListResponse>("/data/programs", {
    params: {
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      keyword: trimmedKeyword,
    },
  });

  return data.items ?? [];
};

const useDebouncedValue = (value: string, delay: number): string => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
};

export interface ProgramSearchOption {
  label: string;
  value: string;
  program: ProgramInfo;
}

export interface UseProgramSearchResult extends Omit<ProgramSearchQueryResult, 'data'> {
  keyword: string;
  debouncedKeyword: string;
  setKeyword: (value: string) => void;
  options: ProgramSearchOption[];
  results: ProgramInfo[];
  reset: () => void;
  // Explicitly include all UseQueryResult properties
  isFetching: boolean;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  data: ProgramInfo[] | undefined;
}

export const useProgramSearch = (initialKeyword = ""): UseProgramSearchResult => {
  const [keyword, setKeyword] = useState(initialKeyword);
  const debouncedKeyword = useDebouncedValue(keyword, SEARCH_DEBOUNCE_MS);
  const isSearchEnabled = debouncedKeyword.trim().length > 0;

  const query = useQuery<ProgramInfo[], Error>({
    queryKey: ["program-search", debouncedKeyword],
    queryFn: () => fetchPrograms(debouncedKeyword),
    enabled: isSearchEnabled,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    setKeyword(initialKeyword);
  }, [initialKeyword]);

  const options = useMemo<ProgramSearchOption[]>(() => {
    if (!query.data || !isSearchEnabled) {
      return [];
    }

    return query.data.map((program) => ({
      label: `${program.title} (${program.programCode})`,
      value: program.programCode,
      program,
    }));
  }, [query.data, isSearchEnabled]);

  const reset = (): void => setKeyword("");

  return {
    keyword,
    debouncedKeyword,
    setKeyword,
    options,
    results: query.data ?? [],
    reset,
    ...query,
  };
};

export default useProgramSearch;

