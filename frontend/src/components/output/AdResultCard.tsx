"use client";

import { Button, Card, Space, Typography, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";
import { copyToClipboard } from "@/lib/clipboard";

const { Text } = Typography;

export interface AdResultCardProps {
  adName: string;
  oneLinkUrl: string;
  index: number;
  className?: string;
}

export default function AdResultCard({
  adName,
  oneLinkUrl,
  index,
  className = "",
}: AdResultCardProps) {
  const handleCopyAdName = async () => {
    const success = await copyToClipboard(adName);
    if (success) {
      message.success(`Ad Name #${index + 1} 已复制到剪贴板`);
    } else {
      message.error("复制失败，请手动复制");
    }
  };

  const handleCopyOneLink = async () => {
    const success = await copyToClipboard(oneLinkUrl);
    if (success) {
      message.success(`OneLink URL #${index + 1} 已复制到剪贴板`);
    } else {
      message.error("复制失败，请手动复制");
    }
  };

  return (
    <Card className={className}>
      <Space direction="vertical" className="w-full" size="small">
        <div className="flex items-center justify-between">
          <Text strong className="text-sm text-gray-600">
            Ad #{index + 1}
          </Text>
        </div>

        {/* Ad Name */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Text type="secondary" className="text-xs">
              Ad Name
            </Text>
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={handleCopyAdName}
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
            {adName}
          </Text>
        </div>

        {/* OneLink URL */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Text type="secondary" className="text-xs">
              OneLink URL
            </Text>
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={handleCopyOneLink}
              size="small"
            >
              复制
            </Button>
          </div>
          <a
            href={oneLinkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full break-all text-sm bg-gray-50 p-2 rounded text-blue-600 hover:text-blue-800 hover:underline"
            style={{ fontFamily: "monospace" }}
            onClick={(e) => {
              // Allow click to open in new tab
              e.stopPropagation();
            }}
          >
            {oneLinkUrl}
          </a>
        </div>
      </Space>
    </Card>
  );
}

