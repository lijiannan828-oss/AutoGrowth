"use client";

import { Card, Progress, Space, Tag, Tooltip } from "antd";
import { formatRelativeTime } from "./utils";
import type { PipelineJobDoc } from "@/features/pipeline/monitor/types";

interface DramaCardProps {
  dramaName: string;
  jobs: PipelineJobDoc[];
}

const getTransferState = (job: PipelineJobDoc) => (job.transfer.status ?? "UNKNOWN").toUpperCase();
const getProcessState = (job: PipelineJobDoc) => (job.process.status ?? "").toUpperCase();
const isTransferComplete = (job: PipelineJobDoc) => {
  const state = getTransferState(job);
  return state === "COMPLETE" || (state !== "TRANSFERRING" && state !== "QUEUED" && getProcessState(job) !== "");
};
const isProcessComplete = (job: PipelineJobDoc) => getProcessState(job) === "COMPLETE";

const calcPercent = (done?: number | null, total?: number | null) => {
  if (done == null || total == null || total <= 0) return undefined;
  return Math.min(100, Math.round((done / total) * 100));
};

const extractLanguageFromPath = (path?: string | null): string | null => {
  if (!path) return null;
  // 尝试从路径中提取语种，例如：Subtitles/en/episode000.srt -> en
  const match = path.match(/\/(en|ko|ja|zh|zh-Hans|ar|es|hi|id|th|ar_translated|es_translated|hi_translated|id_translated|th_translated|zh_translated|zh-Hans_translated)\//i);
  if (match) return match[1];
  return null;
};

const translateError = (errorMessage?: string | null): string => {
  if (!errorMessage) return "未知错误";
  
  // 错误解译映射
  const errorMap: Record<string, string> = {
    "FileNotFoundError": "文件未找到",
    "PermissionError": "权限不足",
    "TimeoutError": "操作超时",
    "ConnectionError": "连接失败",
    "StorageError": "存储错误",
    "ProcessingError": "处理失败",
    "InvalidFormat": "格式无效",
  };
  
  // 尝试匹配常见错误
  for (const [key, value] of Object.entries(errorMap)) {
    if (errorMessage.includes(key)) {
      return value;
    }
  }
  
  // 如果错误信息太长，截取前100个字符
  if (errorMessage.length > 100) {
    return errorMessage.substring(0, 100) + "...";
  }
  
  return errorMessage;
};

export function DramaCard({ dramaName, jobs }: DramaCardProps) {
  // 分离不同类型的任务
  const activeTransferJobs = jobs.filter(
    (job) => !isTransferComplete(job) && getTransferState(job) !== "FAILED"
  );
  const completedTransferCount = jobs.filter(
    (job) => isTransferComplete(job) && getTransferState(job) !== "FAILED"
  ).length;
  
  const activeProcessJobs = jobs.filter(
    (job) => !isProcessComplete(job) && getProcessState(job) !== "FAILED" && getProcessState(job) !== ""
  );
  const completedProcessCount = jobs.filter(isProcessComplete).length;
  
  const failedJobs = jobs.filter(
    (job) => job.failures.length > 0 || getTransferState(job) === "FAILED" || getProcessState(job) === "FAILED" || getProcessState(job) === "FAILED_STAGE2"
  );

  // 找到最新创建的任务时间（用于排序）
  const latestJob = jobs.reduce((latest, job) => {
    if (!job.last_updated) return latest;
    const jobTime = new Date(job.last_updated).getTime();
    const latestTime = latest ? new Date(latest.last_updated!).getTime() : 0;
    return jobTime > latestTime ? job : latest;
  }, jobs[0] as PipelineJobDoc | undefined);

  return (
    <Card
      size="small"
      className="border border-gray-100 shadow-sm"
      title={
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-800">{dramaName}</span>
          {latestJob && (
            <span className="text-xs text-gray-500">
              最新更新：{formatRelativeTime(latestJob.last_updated)}
            </span>
          )}
        </div>
      }
    >
      <Space direction="vertical" size="middle" className="w-full">
        {/* 传输任务区域 */}
        <div className="space-y-2">
          <p className="text-sm font-semibold text-gray-700">传输任务</p>
          {activeTransferJobs.length > 0 && (
            <div className="space-y-2">
              {activeTransferJobs.map((job) => {
                const transferState = getTransferState(job);
                const progressPercent = calcPercent(job.stats?.files_done, job.stats?.files_total);
                return (
                  <div key={job.id} className="border-l-2 border-blue-400 pl-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <code className="text-xs text-gray-600">{job.id}</code>
                      <Tag bordered={false} color="blue">
                        {transferState}
                      </Tag>
                    </div>
                    {job.transfer.progress_text && (
                      <p className="text-xs text-gray-500">{job.transfer.progress_text}</p>
                    )}
                    {progressPercent != null && (
                      <Progress percent={progressPercent} size="small" status="active" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
          {completedTransferCount > 0 && (
            <p className="text-xs text-gray-500">已完成任务数：{completedTransferCount}</p>
          )}
          {activeTransferJobs.length === 0 && completedTransferCount === 0 && (
            <p className="text-xs text-gray-400">暂无传输任务</p>
          )}
        </div>

        {/* 压制任务区域 */}
        <div className="space-y-2">
          <p className="text-sm font-semibold text-gray-700">压制任务</p>
          {activeProcessJobs.length > 0 && (
            <div className="space-y-2">
              {activeProcessJobs.map((job) => {
                const processState = getProcessState(job);
                const progressPercent = calcPercent(job.process.processed_count, job.process.total_count);
                
                // 提取语种信息：优先从 language_details 获取，否则从 file_path 提取
                const languages = Object.keys(job.process?.language_details ?? {});
                let languageInfo = "未知语种";
                if (languages.length > 0) {
                  languageInfo = languages.join(", ");
                } else if (job.failures.length > 0) {
                  const lang = extractLanguageFromPath(job.failures[0]?.file_path);
                  if (lang) languageInfo = lang;
                } else if (job.source_path) {
                  // 尝试从 source_path 提取语种（例如：Subtitles/en/）
                  const lang = extractLanguageFromPath(job.source_path);
                  if (lang) languageInfo = lang;
                }

                return (
                  <div key={job.id} className="border-l-2 border-green-400 pl-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <code className="text-xs text-gray-600">{job.id}</code>
                      <Tag bordered={false} color="green">
                        {languageInfo}
                      </Tag>
                      <Tag bordered={false} color="cyan">
                        {processState}
                      </Tag>
                    </div>
                    {job.process.progress_text && (
                      <p className="text-xs text-gray-500">{job.process.progress_text}</p>
                    )}
                    {progressPercent != null && (
                      <Progress percent={progressPercent} size="small" status="active" />
                    )}
                    {job.process.language_details && Object.keys(job.process.language_details).length > 0 && (
                      <div className="text-xs text-gray-500">
                        {Object.entries(job.process.language_details).map(([lang, meta]) => (
                          <span key={lang} className="mr-2">
                            {lang}: {meta?.done ?? 0}/{meta?.total ?? 0}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          {completedProcessCount > 0 && (
            <p className="text-xs text-gray-500">已完成任务数：{completedProcessCount}</p>
          )}
          {activeProcessJobs.length === 0 && completedProcessCount === 0 && (
            <p className="text-xs text-gray-400">暂无压制任务</p>
          )}
        </div>

        {/* 失败任务区域 */}
        {failedJobs.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-red-600">失败任务</p>
            <div className="space-y-2">
              {failedJobs.map((job) => (
                <div key={job.id} className="border-l-2 border-red-400 pl-3 space-y-1">
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-gray-600">{job.id}</code>
                    <Tag bordered={false} color="red">
                      {getTransferState(job) === "FAILED" ? "传输失败" : getProcessState(job) === "FAILED" || getProcessState(job) === "FAILED_STAGE2" ? "压制失败" : "失败"}
                    </Tag>
                  </div>
                  {job.failures.length > 0 && (
                    <div className="space-y-1">
                      {job.failures.map((failure, idx) => (
                        <Tooltip key={idx} title={failure.error_message ?? "无错误信息"}>
                          <p className="text-xs text-red-600">
                            {translateError(failure.error_message)}
                          </p>
                        </Tooltip>
                      ))}
                    </div>
                  )}
                  {(!job.failures || job.failures.length === 0) && (
                    <p className="text-xs text-red-600">
                      {translateError(job.transfer.status === "FAILED" ? "传输失败" : job.process.status === "FAILED" ? "压制失败" : "未知错误")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Space>
    </Card>
  );
}

