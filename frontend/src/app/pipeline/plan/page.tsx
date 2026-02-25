"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Button,
  Card,
  Empty,
  Result,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Tooltip,
  message,
} from "antd";
import {
  CheckCircleTwoTone,
  CloudUploadOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createTransferJob } from "@/features/pipeline/api";
import type { SelectedFolderNode, TransferRequestPayload } from "@/features/pipeline/types";
import {
  ProgramBrowserTree,
  type ProgramSelection,
} from "@/components/pipeline/ProgramBrowserTree";
import { DirectoryTreeSelector } from "@/components/pipeline/DirectoryTreeSelector";

const formatBytes = (bytes?: number): string => {
  if (!bytes || bytes <= 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
};

export default function PipelinePlanPage() {
  const router = useRouter();
  const [messageApi, contextHolder] = message.useMessage();
  const [selectedProgram, setSelectedProgram] = useState<ProgramSelection | null>(null);
  const [selectedFolders, setSelectedFolders] = useState<SelectedFolderNode[]>([]);
  const [lastSubmission, setLastSubmission] = useState<{ jobId?: string; dramaName: string } | null>(
    null,
  );
  const appEnv =
    process.env.NEXT_PUBLIC_APP_ENV ?? (process.env.NODE_ENV === "production" ? "production" : "development");
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    } finally {
      setRefreshing(false);
    }
  };

  const selectedFoldersMeta = useMemo(() => {
    return {
      count: selectedFolders.length,
      size: 0,
    };
  }, [selectedFolders]);

  const mutation = useMutation({
    mutationFn: (payload: TransferRequestPayload) => createTransferJob(payload),
    onSuccess: (data, variables) => {
      messageApi.success("传输任务已排队");
      setLastSubmission({
        jobId: data.job_id,
        dramaName: variables.drama_name,
      });
      void queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    },
    onError: (error: Error) => {
      messageApi.error(error.message ?? "传输任务创建失败");
    },
  });

  const handleSubmit = () => {
    if (!selectedProgram) {
      messageApi.warning("请先选择需要传输的剧集");
      return;
    }
    if (!selectedFolders.length) {
      messageApi.warning("请至少勾选一个要传输的目录");
      return;
    }
    console.log("当前环境：", appEnv);
    console.log("选中的目录：", selectedFolders);
    mutation.mutate({
      drama_name: selectedProgram.name,
      gdrive_path: selectedProgram.path,
      include_folders: selectedFolders.map((folder) => folder.path),
    });
  };

  const handleProgramSelect = (programMeta: ProgramSelection | null) => {
    setSelectedProgram(programMeta);
    setSelectedFolders([]);
    setLastSubmission(null);
  };

  return (
    <>
      {contextHolder}
      <div className="flex flex-col gap-6 px-4 py-6 md:px-8 lg:px-10">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase font-semibold tracking-widest text-primary">
              Transfer Planner
            </p>
            <h1 className="text-2xl font-bold text-gray-900">选择传输对象</h1>
            <p className="text-sm text-gray-500 mt-1">
              运营专员可在此选择 GDrive 目录、核对传输细节，并一键排队到云端任务。
            </p>
          </div>
          <Space>
            <Tooltip title="刷新 GDrive 目录">
              <Button
                icon={<ReloadOutlined />}
                loading={refreshing}
                onClick={handleRefresh}
              >
                刷新目录
              </Button>
            </Tooltip>
          </Space>
        </div>

        <div className="grid gap-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card
              title="剧集目录"
              variant="borderless"
              className="shadow-sm border border-gray-100"
              extra={
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
                    已传输
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" />
                    未传输
                  </span>
                </div>
              }
            >
              <Space direction="vertical" size="large" className="w-full">
                <ProgramBrowserTree
                  selectedProgramId={selectedProgram?.id}
                  onSelect={handleProgramSelect}
                />
                <p className="text-xs text-gray-500">
                  提示：展开 KR/JP/US 节点后按需加载剧集列表，避免一次性扫描全部数据。
                </p>
              </Space>
            </Card>

            <Card
              title={
                <div className="flex items-center gap-2">
                  <span>目录勾选</span>
                  {selectedProgram && (
                    <Tag color="default" bordered={false}>
                      {selectedProgram.name}
                    </Tag>
                  )}
                </div>
              }
              variant="borderless"
              className="shadow-sm border border-gray-100"
              extra={
                selectedProgram && (
                  <Space size="small" className="text-xs text-gray-500">
                    <InfoCircleOutlined />
                    {selectedProgram.path}
                  </Space>
                )
              }
            >
              {selectedProgram && (
                <div className="mb-4">
                  <Alert
                    type={selectedProgram.inGcs ? "success" : "warning"}
                    showIcon
                    message={
                      selectedProgram.inGcs
                        ? "GCS 中已存在同名目录，本次传输会覆盖新增文件"
                        : "GCS 中尚未发现该剧集，建议立即传输"
                    }
                  />
                </div>
              )}
              <DirectoryTreeSelector
                program={selectedProgram}
                value={selectedFolders}
                onChange={setSelectedFolders}
              />
            </Card>
          </div>

          <Card
            title="传输确认"
            variant="borderless"
            className="shadow-sm border border-gray-100 flex flex-col gap-4"
          >
            {selectedProgram ? (
              <>
                <div className="grid grid-cols-1 gap-4">
                  <Statistic
                    title="预计目录数量"
                    value={selectedFoldersMeta.count}
                    suffix="个"
                  />
                  <Statistic title="总体积 (估算)" value={formatBytes(undefined)} />
                </div>
                <div className="rounded-lg border border-dashed border-gray-200 p-3 text-xs">
                  <p className="font-semibold text-gray-500 mb-1">目标 GCS 路径</p>
                  <code className="text-sm text-gray-800">
                    vigloo_source/{selectedProgram.name}
                  </code>
                </div>
                <div className="rounded-lg bg-gray-50 border border-dashed border-gray-200 p-4 space-y-2">
                  <p className="text-xs font-semibold text-gray-500">将传输以下目录：</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedFolders.map((folder) => (
                      <Tag key={folder.id} className="text-xs" bordered={false} color="blue">
                        {folder.path}
                      </Tag>
                    ))}
                    {!selectedFolders.length && (
                      <span className="text-xs text-gray-400">暂无选择</span>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="请选择左侧剧集以查看摘要"
              />
            )}

            {lastSubmission && (
              <Result
                status="success"
                icon={<CheckCircleTwoTone twoToneColor="#52c41a" />}
                title="传输任务已排队"
                subTitle={
                  lastSubmission.jobId
                    ? `Job ID: ${lastSubmission.jobId}`
                    : "已提交到 Cloud Run Jobs"
                }
                extra={[
                  <Button
                    type="primary"
                    key="monitor"
                    onClick={() => router.push("/pipeline/monitor")}
                  >
                    查看任务监控
                  </Button>,
                  <Button key="reset" onClick={() => setLastSubmission(null)}>
                    继续排队
                  </Button>,
                ]}
              />
            )}

            <Tooltip
              title={!selectedProgram ? "请选择剧集" : !selectedFolders.length ? "请选择目录" : ""}
            >
              <Button
                type="primary"
                size="large"
                icon={<CloudUploadOutlined />}
                disabled={!selectedProgram || !selectedFolders.length}
                loading={mutation.isPending}
                onClick={handleSubmit}
                className="w-full"
              >
                开始传输
              </Button>
            </Tooltip>
          </Card>
        </div>
      </div>
    </>
  );
}

