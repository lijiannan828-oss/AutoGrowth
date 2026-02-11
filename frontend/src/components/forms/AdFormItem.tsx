"use client";

import { Button, Form, Input, Select, Space } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { Controller } from "react-hook-form";
import type { Control, FieldErrors } from "react-hook-form";
import type { StrategyFormData } from "@/types/form";
import { CREATIVE_TYPES_V2, AD_LANGUAGES, TEAMS, DESIGNERS } from "@/lib/constants";

export interface AdFormItemProps {
  index: number;
  control: Control<StrategyFormData>;
  errors: FieldErrors<StrategyFormData>;
  onRemove: () => void;
  canRemove: boolean;
}

export default function AdFormItem({
  index,
  control,
  errors,
  onRemove,
  canRemove,
}: AdFormItemProps) {
  const adErrors = errors.ads?.[index];

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-base font-semibold">Ad {index + 1}</h4>
        {canRemove && (
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={onRemove}
            size="small"
          >
            删除
          </Button>
        )}
      </div>

      {/* 新命名规则 - 广告字段 */}
      {/* 格式: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他} */}
      <Space direction="vertical" className="w-full" size="middle">
        <Form.Item
          label="戏剧ID (Drama ID)"
          required
          validateStatus={adErrors?.dramaId ? "error" : ""}
          help={adErrors?.dramaId?.message}
        >
          <Controller
            name={`ads.${index}.dramaId`}
            control={control}
            rules={{ required: "请输入戏剧ID" }}
            render={({ field }) => (
              <Input {...field} placeholder="输入戏剧ID (如 10000235)" />
            )}
          />
        </Form.Item>

        <Form.Item
          label="语言 (Language)"
          required
          validateStatus={adErrors?.language ? "error" : ""}
          help={adErrors?.language?.message}
        >
          <Controller
            name={`ads.${index}.language`}
            control={control}
            rules={{ required: "请选择语言" }}
            render={({ field }) => (
              <Select {...field} placeholder="选择语言" options={AD_LANGUAGES} />
            )}
          />
        </Form.Item>

        <Form.Item
          label="团队 (Team)"
          required
          validateStatus={adErrors?.team ? "error" : ""}
          help={adErrors?.team?.message}
        >
          <Controller
            name={`ads.${index}.team`}
            control={control}
            rules={{ required: "请选择团队" }}
            render={({ field }) => (
              <Select {...field} placeholder="选择团队" options={TEAMS} />
            )}
          />
        </Form.Item>

        <Form.Item
          label="设计师 (Designer)"
          required
          validateStatus={adErrors?.designer ? "error" : ""}
          help={adErrors?.designer?.message}
        >
          <Controller
            name={`ads.${index}.designer`}
            control={control}
            rules={{ required: "请选择设计师" }}
            render={({ field }) => (
              <Select {...field} placeholder="选择设计师" options={DESIGNERS} />
            )}
          />
        </Form.Item>

        <Form.Item
          label="日期 (Date)"
          required
          validateStatus={adErrors?.date ? "error" : ""}
          help={adErrors?.date?.message}
        >
          <Controller
            name={`ads.${index}.date`}
            control={control}
            rules={{ required: "请输入日期" }}
            render={({ field }) => (
              <Input {...field} placeholder="输入日期 MMDD (如 1205)" />
            )}
          />
        </Form.Item>

        <Form.Item
          label="类型 (Creative Type)"
          required
          validateStatus={adErrors?.creativeType ? "error" : ""}
          help={adErrors?.creativeType?.message}
        >
          <Controller
            name={`ads.${index}.creativeType`}
            control={control}
            rules={{ required: "请选择创意类型" }}
            render={({ field }) => (
              <Select {...field} placeholder="选择创意类型" options={CREATIVE_TYPES_V2} />
            )}
          />
        </Form.Item>

        <Form.Item
          label="数字 (Number)"
          validateStatus={adErrors?.number ? "error" : ""}
          help={adErrors?.number?.message}
        >
          <Controller
            name={`ads.${index}.number`}
            control={control}
            render={({ field }) => (
              <Input {...field} placeholder="输入数字或范围 (如 01, 01-05)" />
            )}
          />
        </Form.Item>

        <Form.Item
          label="其他 (Optional)"
          validateStatus={adErrors?.optional ? "error" : ""}
          help={adErrors?.optional?.message}
        >
          <Controller
            name={`ads.${index}.optional`}
            control={control}
            render={({ field }) => (
              <Input {...field} placeholder="输入可选后缀 (如 txt, ctn)" />
            )}
          />
        </Form.Item>
      </Space>
    </div>
  );
}

