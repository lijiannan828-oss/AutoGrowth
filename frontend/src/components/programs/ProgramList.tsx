"use client";

import { useEffect, useMemo, useRef } from "react";
import { Empty, Spin } from "antd";

import ProgramCard from "./ProgramCard";
import type { ProgramInfo } from "@/types/api";

export interface ProgramListProps {
  programs: ProgramInfo[];
  isLoading?: boolean;
  isFetching?: boolean;
  isFetchingNextPage?: boolean;
  hasMore?: boolean;
  highlightKeyword?: string;
  selectedProgramCode?: string;
  onSelect?: (program: ProgramInfo) => void;
  onAction?: (program: ProgramInfo) => void;
  onLoadMore?: () => void;
}

const ProgramList = ({
  programs,
  isLoading = false,
  isFetching = false,
  isFetchingNextPage = false,
  hasMore = false,
  highlightKeyword,
  selectedProgramCode,
  onSelect,
  onAction,
  onLoadMore,
}: ProgramListProps) => {
  const normalizedKeyword = highlightKeyword?.trim().toLowerCase() ?? "";
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const programIds = useMemo(() => programs.map((program) => program.programCode), [programs]);

  useEffect(() => {
    if (!selectedProgramCode) return;
    if (!programIds.includes(selectedProgramCode)) return;

    const element = document.getElementById(`program-card-${selectedProgramCode}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
      element.classList.add("ring-2", "ring-blue-500");
      const timer = window.setTimeout(() => {
        element.classList.remove("ring-2", "ring-blue-500");
      }, 1600);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [selectedProgramCode, programIds]);

  useEffect(() => {
    if (!hasMore || !onLoadMore) return;
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry?.isIntersecting && !isFetchingNextPage) {
          onLoadMore();
        }
      },
      {
        rootMargin: "200px",
      },
    );

    observer.observe(sentinel);

    return () => observer.disconnect();
  }, [hasMore, onLoadMore, isFetchingNextPage, programs.length]);

  if (isLoading && programs.length === 0) {
    return (
      <div className="flex justify-center py-8">
        <Spin size="large" />
      </div>
    );
  }

  if (!isLoading && programs.length === 0) {
    return <Empty description="暂无剧目数据" />;
  }

  return (
    <div className="relative space-y-2">
      {isFetching && (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex justify-center">
          <Spin size="small" className="bg-white/80 px-3 py-1 text-xs" />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {programs.map((program) => (
          <div key={program.programCode}>
            <ProgramCard
              program={program}
              isSelected={program.programCode === selectedProgramCode}
              highlightKeyword={normalizedKeyword}
              onSelect={() => onSelect?.(program)}
              onAction={() => onAction?.(program)}
            />
          </div>
        ))}
      </div>

      {hasMore && (
        <div ref={sentinelRef} className="flex justify-center py-4">
          {isFetchingNextPage ? (
            <Spin />
          ) : (
            <span className="text-sm text-gray-500">向下滚动加载更多</span>
          )}
        </div>
      )}
    </div>
  );
};

export default ProgramList;

