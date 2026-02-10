"use client";

import { useMemo } from "react";
import { ArrowRightOutlined } from "@ant-design/icons";
import { Button, Card, Space, Tag, Tooltip, Typography } from "antd";

import type { ProgramInfo } from "@/types/api";

export interface ProgramCardProps {
  program: ProgramInfo;
  isSelected?: boolean;
  highlightKeyword?: string;
  onSelect?: () => void;
  onAction?: () => void;
}

const highlightText = (text: string, keyword?: string) => {
  if (!keyword) return text;
  const lowerKeyword = keyword.toLowerCase();
  const lowerText = text.toLowerCase();
  const index = lowerText.indexOf(lowerKeyword);
  if (index === -1) return text;

  const before = text.slice(0, index);
  const match = text.slice(index, index + keyword.length);
  const after = text.slice(index + keyword.length);

  return (
    <>
      {before}
      <mark className="rounded bg-yellow-200 px-1 py-0.5">{match}</mark>
      {after}
    </>
  );
};

const ProgramCard = ({
  program,
  isSelected = false,
  highlightKeyword,
  onSelect,
  onAction,
}: ProgramCardProps) => {
  const releaseDate = useMemo(
    () => (program.releaseDate ? new Date(program.releaseDate).toLocaleDateString() : "未知"),
    [program.releaseDate],
  );

  return (
    <Card
      id={`program-card-${program.programCode}`}
      hoverable
      onClick={onSelect}
      className={`h-full transition-shadow duration-200 ${
        isSelected ? "border-blue-500 shadow-lg" : "border-slate-200"
      }`}
      title={
        <Space direction="vertical" size={2} className="w-full">
          <Typography.Title level={5} className="!mb-0 line-clamp-1" title={program.title}>
            {highlightText(program.title, highlightKeyword)}
          </Typography.Title>
          <Typography.Text type="secondary" className="font-mono text-xs">
            {highlightText(program.programCode, highlightKeyword)}
          </Typography.Text>
        </Space>
      }
      actions={[
        <Tooltip key="create" title="去创建广告">
          <Button
            type={isSelected ? "primary" : "default"}
            shape="circle"
            icon={<ArrowRightOutlined />}
            onClick={(event) => {
              event.stopPropagation();
              onAction?.();
            }}
          />
        </Tooltip>,
      ]}
    >
      <Space direction="vertical" size="small" className="w-full">
        {program.subTitle && (
          <Typography.Text className="text-sm text-gray-600 line-clamp-2">
            {highlightText(program.subTitle, highlightKeyword)}
          </Typography.Text>
        )}

        <Space size={[8, 8]} wrap>
          <Tag color={isSelected ? "blue" : "default"}>集数 {program.episodeCount}</Tag>
          <Tag color="green">上线 {releaseDate}</Tag>
        </Space>

        {program.synopsis && (
          <Tooltip title={program.synopsis}>
            <Typography.Paragraph ellipsis={{ rows: 3 }} className="!mb-0 text-xs text-gray-500">
              {highlightText(program.synopsis, highlightKeyword)}
            </Typography.Paragraph>
          </Tooltip>
        )}

        {program.contentInformation && (
          <Typography.Text className="text-xs text-gray-500">
            内容标签：{program.contentInformation}
          </Typography.Text>
        )}
      </Space>
    </Card>
  );
};

export default ProgramCard;

