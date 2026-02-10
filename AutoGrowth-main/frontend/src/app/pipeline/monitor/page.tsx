"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  Empty,
  Skeleton,
  Space,
  Tooltip,
} from "antd";
import { CloudOutlined, InfoCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import { usePipelineJobs } from "@/features/pipeline/monitor/usePipelineJobs";
import type { PipelineJobDoc } from "@/features/pipeline/monitor/types";
import { StatusTabs, type StatusTabKey } from "@/components/pipeline/monitor/StatusTabs";
import { DramaCard } from "@/components/pipeline/monitor/DramaCard";

// 筛选逻辑函数
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

const isCompletedInLast30Days = (job: PipelineJobDoc) => {
  const processState = getProcessState(job);
  if (processState !== "COMPLETE") return false;
  if (!job.last_updated) return false;
  const lastUpdated = new Date(job.last_updated);
  const now = new Date();
  const diffDays = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);
  return diffDays <= 30;
};

// 按状态筛选任务
const filterJobsByTab = (jobs: PipelineJobDoc[], tabKey?: StatusTabKey): PipelineJobDoc[] => {
  if (!tabKey) return jobs;
  
  switch (tabKey) {
    case "in_progress":
      return jobs.filter(isInProgress);
    case "transferring":
      return jobs.filter(isTransferring);
    case "processing":
      return jobs.filter(isProcessing);
    case "failed":
      return jobs.filter(isFailed);
    case "completed":
      return jobs.filter(isCompletedInLast30Days);
    default:
      return jobs;
  }
};

// 按 drama_name 聚合任务
interface DramaGroup {
  dramaName: string;
  jobs: PipelineJobDoc[];
  latestCreatedAt: number;
}

const groupJobsByDrama = (jobs: PipelineJobDoc[]): DramaGroup[] => {
  const groups = new Map<string, PipelineJobDoc[]>();
  
  // 按 drama_name 分组
  jobs.forEach((job) => {
    const dramaName = job.drama_name;
    if (!groups.has(dramaName)) {
      groups.set(dramaName, []);
    }
    groups.get(dramaName)!.push(job);
  });
  
  // 转换为数组并计算最新创建时间
  return Array.from(groups.entries()).map(([dramaName, dramaJobs]) => {
    const latestCreatedAt = dramaJobs.reduce((max, job) => {
      if (!job.last_updated) return max;
      const jobTime = new Date(job.last_updated).getTime();
      return Math.max(max, jobTime);
    }, 0);
    
    return {
      dramaName,
      jobs: dramaJobs,
      latestCreatedAt,
    };
  });
};

// 排序：按最新创建的任务排序
const sortDramaGroups = (groups: DramaGroup[]): DramaGroup[] => {
  return [...groups].sort((a, b) => b.latestCreatedAt - a.latestCreatedAt);
};

export default function PipelineMonitorPage() {
  const { jobs, loading, error, reload } = usePipelineJobs();
  const [activeTab, setActiveTab] = useState<StatusTabKey | undefined>();

  // 根据选中的 Tab 筛选任务
  const filteredJobs = useMemo(() => filterJobsByTab(jobs, activeTab), [jobs, activeTab]);

  // 按 drama_name 聚合任务
  const dramaGroups = useMemo(() => {
    const groups = groupJobsByDrama(filteredJobs);
    return sortDramaGroups(groups);
  }, [filteredJobs]);

  return (
    <div className="flex flex-col gap-6 px-4 py-6 md:px-8 lg:px-10">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase font-semibold tracking-widest text-primary">
            Operations Monitor
          </p>
          <h1 className="text-2xl font-bold text-gray-900">任务监控</h1>
          <p className="text-sm text-gray-500 mt-1">
            实时查看传输/压制任务状态，支持快速重试或跳转至资源库。
          </p>
        </div>
        <Space wrap>
          <Link href="/pipeline/plan">
            <Button icon={<CloudOutlined />}>发起新传输</Button>
          </Link>
          <Tooltip title="点击刷新或等待后台自动轮询">
            <Button icon={<ReloadOutlined />} onClick={reload}>
              手动刷新
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* Tab 筛选栏 */}
      <StatusTabs
        jobs={jobs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onClearFilter={() => setActiveTab(undefined)}
      />

      {error && <Alert type="error" showIcon message={error} />}

      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : dramaGroups.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={activeTab ? "当前筛选条件下暂无任务" : "暂无任务，请前往传输计划页发起新任务"}
        />
      ) : (
        <div className="grid gap-4">
          {dramaGroups.map((group) => (
            <DramaCard key={group.dramaName} dramaName={group.dramaName} jobs={group.jobs} />
          ))}
        </div>
      )}

      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="提示"
        description="此页面每 15 秒轮询一次任务列表。如需更快响应，可点击上方“手动刷新”按钮。"
      />
    </div>
  );
}

