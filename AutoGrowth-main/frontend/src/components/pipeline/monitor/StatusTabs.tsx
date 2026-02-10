"use client";

import { Button, Tabs } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import type { PipelineJobDoc } from "@/features/pipeline/monitor/types";

export type StatusTabKey = "in_progress" | "transferring" | "processing" | "failed" | "completed";

interface StatusTabsProps {
  jobs: PipelineJobDoc[];
  activeTab?: StatusTabKey;
  onTabChange?: (key: StatusTabKey) => void;
  onClearFilter?: () => void;
}

const getTransferState = (job: PipelineJobDoc) => (job.transfer.status ?? "UNKNOWN").toUpperCase();
const getProcessState = (job: PipelineJobDoc) => (job.process.status ?? "").toUpperCase();
const hasTransferFailure = (job: PipelineJobDoc) =>
  job.failures.some((failure) => failure.stage === "transfer");
const hasProcessFailure = (job: PipelineJobDoc) =>
  job.failures.some((failure) => failure.stage === "process");

const isInProgress = (job: PipelineJobDoc) => {
  const transferState = getTransferState(job);
  const processState = getProcessState(job);
  const isComplete = processState === "COMPLETE";
  const isFailed = transferState === "FAILED" || processState === "FAILED" || processState === "FAILED_STAGE2";
  return !isComplete && !isFailed;
};

const isTransferring = (job: PipelineJobDoc) => {
  const state = getTransferState(job);
  if (hasTransferFailure(job)) return false;
  // stage=1 且 status=TRANSFERRING 或 QUEUED
  return state === "TRANSFERRING" || state === "QUEUED";
};

const isProcessing = (job: PipelineJobDoc) => {
  const state = getProcessState(job);
  if (hasProcessFailure(job)) return false;
  // 已传输完成在压制中：stage=2 且 status=PROCESSING
  // 单独在压制：type=manual 且 stage=1 且 status=PROCESSING
  if (state === "PROCESSING") return true;
  // 检查是否是 manual 类型且 stage=1 的压制任务
  if (job.job_type === "manual" && state === "PROCESSING") return true;
  return false;
};

const isFailed = (job: PipelineJobDoc) => {
  const transferState = getTransferState(job);
  const processState = getProcessState(job);
  return (
    transferState === "FAILED" ||
    processState === "FAILED" ||
    processState === "FAILED_STAGE2" ||
    hasTransferFailure(job) ||
    hasProcessFailure(job)
  );
};

const isCompleted = (job: PipelineJobDoc) => {
  const processState = getProcessState(job);
  return processState === "COMPLETE";
};

const isCompletedInLast30Days = (job: PipelineJobDoc) => {
  if (!isCompleted(job)) return false;
  if (!job.last_updated) return false;
  const lastUpdated = new Date(job.last_updated);
  const now = new Date();
  const diffDays = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);
  return diffDays <= 30;
};

export function StatusTabs({ jobs, activeTab, onTabChange, onClearFilter }: StatusTabsProps) {
  const inProgressCount = jobs.filter(isInProgress).length;
  const transferringCount = jobs.filter(isTransferring).length;
  const processingCount = jobs.filter(isProcessing).length;
  const failedCount = jobs.filter(isFailed).length;
  const completedCount = jobs.filter(isCompletedInLast30Days).length;

  const items = [
    {
      key: "in_progress" as StatusTabKey,
      label: `进行中的任务 (${inProgressCount})`,
    },
    {
      key: "transferring" as StatusTabKey,
      label: `传输中 (${transferringCount})`,
    },
    {
      key: "processing" as StatusTabKey,
      label: `压制中 (${processingCount})`,
    },
    {
      key: "failed" as StatusTabKey,
      label: `失败任务 (${failedCount})`,
    },
    {
      key: "completed" as StatusTabKey,
      label: `已完成任务 (${completedCount})`,
    },
  ];

  return (
    <div className="flex items-center justify-between gap-4">
      <Tabs
        activeKey={activeTab}
        onChange={(key) => onTabChange?.(key as StatusTabKey)}
        items={items}
        className="flex-1"
      />
      {activeTab && (
        <Button
          icon={<CloseOutlined />}
          onClick={onClearFilter}
          size="small"
        >
          清除筛选
        </Button>
      )}
    </div>
  );
}

