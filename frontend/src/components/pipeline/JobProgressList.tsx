"use client";

import { Card, Progress, Space, Tag, Typography } from "antd";
import { usePipelineJobs } from "@/hooks/usePipelineJobs";

const { Text } = Typography;

export function JobProgressList() {
  const { jobs, loading, error } = usePipelineJobs(20);
  const activeJobs = jobs.filter((job) => {
    const transferState = (job.transfer.status ?? "").toUpperCase();
    const processState = (job.process.status ?? "").toUpperCase();
    return ["QUEUED", "TRANSFERRING", "PROCESSING"].some(
      (state) => transferState === state || processState === state,
    );
  });

  return (
    <Card
      title="实时任务进度"
      className="shadow-sm border border-gray-100"
      extra={<Tag bordered={false}>{activeJobs.length} 个进行中</Tag>}
      loading={loading}
    >
      {error && (
        <Text type="danger" className="block mb-2">
          {error}
        </Text>
      )}
      {activeJobs.length === 0 ? (
        <Text type="secondary">暂无进行中的任务</Text>
      ) : (
        <Space direction="vertical" size="large" className="w-full">
          {activeJobs.map((job) => {
            const total = job.stats?.files_total ?? 0;
            const done = job.stats?.files_done ?? 0;
            const percent = total > 0 ? Math.round((done / total) * 100) : 0;
            return (
              <div key={job.id} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{job.drama_name}</span>
                  <span className="text-xs text-gray-500">
                    {done}/{total || "-"} 文件
                  </span>
                </div>
                <Progress percent={percent} size="small" status="active" />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>速度 {job.stats?.speed_bps ? `${(job.stats.speed_bps / (1024 * 1024)).toFixed(1)} MB/s` : "-"}</span>
                  <span>更新 {job.last_updated ? new Date(job.last_updated).toLocaleTimeString() : "-"}</span>
                </div>
              </div>
            );
          })}
        </Space>
      )}
    </Card>
  );
}


