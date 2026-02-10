"use client";

import { useMemo } from "react";
import { Alert, Card, Empty, Progress, Table, Tag, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import { usePipelineStatus, type PipelineStatusRow } from "@/hooks/usePipelineStatus";
export default function StatusTable() {
  const { rows, isLoading, error } = usePipelineStatus();

  const columns: ColumnsType<PipelineStatusRow> = [
    {
      title: "分类",
      dataIndex: "category",
      width: 140,
      filters: [
        ...Array.from(new Set(rows.map((row) => row.category))).map((category) => ({
          text: category,
          value: category,
        })),
      ],
      onFilter: (value, record) => record.category === value,
    },
    {
      title: "Program",
      dataIndex: "programCode",
      render: (code, record) => (
        <div className="flex flex-col">
          <span className="font-semibold">{code}</span>
          <span className="text-xs text-gray-500">{record.name}</span>
        </div>
      ),
    },
    {
      title: "GCS 状态",
      dataIndex: "in_gcs",
      render: (inGcs: boolean) => (
        <Tag color={inGcs ? "green" : "orange"} bordered={false}>
          {inGcs ? "已存在" : "未同步"}
        </Tag>
      ),
    },
    {
      title: "文件进度",
      key: "progress",
      render: (_, record) => {
        const total = record.files_total ?? record.total_size_bytes ?? 0;
        const done = record.files_in_gcs ?? 0;
        const percent =
          record.files_total && record.files_total > 0
            ? Math.round((done / record.files_total) * 100)
            : undefined;
        return (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">
              {record.files_in_gcs ?? 0}/{record.files_total ?? "-"}
            </span>
            <Progress percent={percent ?? 0} size="small" status={percent === 100 ? "success" : "active"} />
          </div>
        );
      },
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      render: (value?: string) =>
        value ? new Date(value).toLocaleString() : "-",
    },
  ];

  return (
    <Card
      title="GDrive / GCS 状态"
      extra={
        <Tooltip title="后台 API 目前为占位，如需真实数据请实现对应端点">
          <Tag color="blue" bordered={false}>
            数据来源：API
          </Tag>
        </Tooltip>
      }
      className="shadow-sm border border-gray-100"
    >
      {error && (
        <Alert
          type="error"
          showIcon
          message="无法加载 GDrive 状态"
          description={error instanceof Error ? error.message : "请稍后重试"}
          className="mb-4"
        />
      )}

      <Table
        dataSource={rows}
        columns={columns}
        loading={isLoading}
        rowKey={(record) => record.path}
        locale={{
          emptyText: <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />,
        }}
        pagination={{ pageSize: 10, showSizeChanger: false }}
      />
    </Card>
  );
}

