"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { GenerationRequest, GenerationResponse } from "@/types/generation";

/**
 * Hook for generating campaign names and OneLink URLs.
 */
export function useGeneration() {
  const mutation = useMutation<GenerationResponse, Error, GenerationRequest>({
    mutationFn: async (request: GenerationRequest) => {
      const response = await apiClient.post<GenerationResponse>(
        "/generate/all",
        request
      );
      return response.data;
    },
  });

  return {
    generate: mutation.mutate,
    generateAsync: mutation.mutateAsync,
    isLoading: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    data: mutation.data,
    reset: mutation.reset,
  };
}


