"use client";

import { Button, Card, Space, Typography, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";
import { copyToClipboard } from "@/lib/clipboard";

const { Text } = Typography;

export interface ResultCardProps {
  label: string;
  value: string;
  className?: string;
}

export default function ResultCard({
  label,
  value,
  className = "",
}: ResultCardProps) {
  const handleCopy = async () => {
    const success = await copyToClipboard(value);
    if (success) {
      message.success(`${label} 已复制到剪贴板`);
    } else {
      message.error("复制失败，请手动复制");
    }
  };

  return (
    <Card className={className}>
      <Space direction="vertical" className="w-full" size="small">
        <div className="flex items-center justify-between">
          <Text strong className="text-sm text-gray-600">
            {label}
          </Text>
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={handleCopy}
            size="small"
          >
            复制
          </Button>
        </div>
        <Text
          code
          className="block w-full break-all text-sm bg-gray-50 p-2 rounded"
          style={{ fontFamily: "monospace" }}
        >
          {value}
        </Text>
      </Space>
    </Card>
  );
}


