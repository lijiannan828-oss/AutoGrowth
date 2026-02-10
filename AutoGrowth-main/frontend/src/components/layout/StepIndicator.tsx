"use client";

import { Steps } from "antd";

export interface StepIndicatorProps {
  current: 1 | 2 | 3;
  className?: string;
}

const stepItems = [
  {
    title: "选择剧目",
    description: "从列表中选择或搜索要投放的剧目",
  },
  {
    title: "填写策略",
    description: "配置 Campaign、Ad Set 和 Ad 参数",
  },
  {
    title: "复制结果",
    description: "查看并复制生成的命名和链接",
  },
];

export default function StepIndicator({
  current,
  className = "",
}: StepIndicatorProps) {
  return (
    <div className={`bg-white border-b border-gray-200 ${className}`}>
      <div className="container mx-auto px-4 py-4 md:py-6">
        <Steps
          current={current - 1}
          items={stepItems}
          size="small"
          className="max-w-3xl mx-auto"
          responsive={true}
        />
      </div>
    </div>
  );
}

