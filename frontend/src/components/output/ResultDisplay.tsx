"use client";

import { Card, Space, Typography, Spin, Alert } from "antd";
import ResultCard from "./ResultCard";
import type { GenerationResponse } from "@/types/generation";

const { Title } = Typography;

export interface ResultDisplayProps {
  data: GenerationResponse | null;
  isLoading?: boolean;
  error?: Error | null;
  className?: string;
}

export default function ResultDisplay({
  data,
  isLoading = false,
  error = null,
  className = "",
}: ResultDisplayProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <div className="py-8 text-center">
          <Spin size="large" />
          <p className="mt-4 text-gray-600">正在生成...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <Alert
          message="生成失败"
          description={error.message || "生成过程中发生错误，请重试"}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className={className}>
      <div className="mb-4">
        <Title level={3} className="!mb-2">
          步骤 3：复制结果
        </Title>
        <p className="text-gray-600 text-sm md:text-base">
          生成完成！请复制以下结果到您的投放平台
        </p>
      </div>

      <Space direction="vertical" className="w-full" size="large">
        {/* Ad Set Name */}
        <ResultCard
          label="Ad Set Name (广告组名称)"
          value={data.adSetName}
        />

        {/* Ad Results */}
        {data.adResults.length > 0 && (
          <Card>
            <Title level={4} className="!mb-4">
              Ad 结果 ({data.adResults.length} 个)
            </Title>
            <Space direction="vertical" className="w-full" size="middle">
              {data.adResults.map((adResult, index) => (
                <ResultCard
                  key={index}
                  label={`Ad ${index + 1} Name (广告名称)`}
                  value={adResult.adName}
                />
              ))}
            </Space>
          </Card>
        )}
      </Space>
    </div>
  );
}
