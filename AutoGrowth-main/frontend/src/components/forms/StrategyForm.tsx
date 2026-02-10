"use client";

import { useEffect, useRef } from "react";
import { Button, Card, Form, Input, Select, Space } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useFieldArray, useForm, Controller, FormProvider, useWatch, type Resolver, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { StrategyFormData } from "@/types/form";
import { strategyFormSchema } from "@/types/strategySchema";
import {
  COUNTRIES,
  MEDIA_SOURCES,
  OPTIMIZATION_TYPES,
  OS_TYPES,
  MAX_AD_COUNT,
  OPTIMIZERS,
  AD_LANGUAGES,
} from "@/lib/constants";
import AdFormItem from "./AdFormItem";

// 使用共享的 Zod schema（与类型保持一致）

export interface StrategyFormProps {
  loggedInUser?: string;
  programId?: string; // 剧集ID，从选中的剧目自动获取
  onSubmit?: (data: StrategyFormData) => void;
  defaultValues?: Partial<StrategyFormData>;
}

// 获取今天的日期，格式为 MMDD
const getTodayDate = () => {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${month}${day}`;
};

export default function StrategyForm({
  loggedInUser = "",
  programId = "",
  onSubmit,
  defaultValues,
}: StrategyFormProps) {
  const todayDate = getTodayDate();

  const methods = useForm<StrategyFormData>({
    resolver: zodResolver(strategyFormSchema) as Resolver<StrategyFormData>,
    defaultValues: defaultValues || {
      // 新命名规则 - 广告组默认值
      adset: {
        country: "",
        language: "",
        mediaSource: "fb",
        os: "w2a",
        optimizer: "",
        date: todayDate, // 默认今天日期
        dramaId: programId, // 自动填充剧集ID
        event: "purchase",
        optional: "",
      },
      // 新命名规则 - 广告默认值
      ads: [
        {
          dramaId: programId, // 自动填充剧集ID
          language: "",
          team: "",
          designer: "",
          date: todayDate, // 默认今天日期
          creativeType: "",
          number: "",
          optional: "",
        },
      ],
    },
  });

  const { control, handleSubmit, formState: { errors }, setValue, getValues } = methods;

  const { fields, append, remove } = useFieldArray({
    control,
    name: "ads",
  });

  // 当 programId 变化时，更新表单中的 dramaId 字段
  useEffect(() => {
    if (programId) {
      setValue("adset.dramaId", programId);
      const ads = getValues("ads");
      ads.forEach((_, index) => {
        setValue(`ads.${index}.dramaId`, programId);
      });
    }
  }, [programId, setValue, getValues]);

  // 监听 Ad Set 中的共享字段
  const adsetDramaId = useWatch({ control, name: "adset.dramaId" });
  const adsetLanguage = useWatch({ control, name: "adset.language" });
  const adsetDate = useWatch({ control, name: "adset.date" });

  // 单向联动：Ad Set → 所有 Ad 同步
  // Ad 中的字段可以单独修改，不会反向同步到 Ad Set
  useEffect(() => {
    const ads = getValues("ads");
    ads.forEach((_, index) => {
      if (adsetDramaId) setValue(`ads.${index}.dramaId`, adsetDramaId);
      if (adsetLanguage) setValue(`ads.${index}.language`, adsetLanguage);
      if (adsetDate) setValue(`ads.${index}.date`, adsetDate);
    });
  }, [adsetDramaId, adsetLanguage, adsetDate, setValue, getValues]);

  const canAddMore = fields.length < MAX_AD_COUNT;
  const canRemove = fields.length > 1;

  const handleAddAd = () => {
    if (canAddMore) {
      // 新增 Ad 时继承上一个 Ad 的所有字段（除了数字）
      const ads = getValues("ads");
      const lastAd = ads[ads.length - 1];
      append({
        dramaId: lastAd?.dramaId || programId,
        language: lastAd?.language || "",
        team: lastAd?.team || "",
        designer: lastAd?.designer || "",
        date: lastAd?.date || todayDate,
        creativeType: lastAd?.creativeType || "",
        number: "", // 数字不继承，需要用户手动填写
        optional: lastAd?.optional || "",
      });
    }
  };

  const handleRemoveAd = (index: number) => {
    if (canRemove) {
      remove(index);
    }
  };

  const onFormSubmit: SubmitHandler<StrategyFormData> = (data) => {
    onSubmit?.(data);
  };

  return (
    <FormProvider {...methods}>
      <Form layout="vertical" onFinish={handleSubmit(onFormSubmit)}>
      <Space direction="vertical" className="w-full" size="large">
        {/* Ad Set 区域 - 新命名规则 */}
        {/* 格式: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他} */}
        <Card title="广告组配置 (Ad Set)" className="w-full">
          <Space direction="vertical" className="w-full" size="middle">
            <Form.Item
              label="国家 (Country)"
              required
              validateStatus={errors.adset?.country ? "error" : ""}
              help={errors.adset?.country?.message}
            >
              <Controller
                name="adset.country"
                control={control}
                render={({ field }) => (
                  <Select {...field} placeholder="选择国家" options={COUNTRIES} />
                )}
              />
            </Form.Item>

            <Form.Item
              label="语言 (Language)"
              required
              validateStatus={errors.adset?.language ? "error" : ""}
              help={errors.adset?.language?.message}
            >
              <Controller
                name="adset.language"
                control={control}
                render={({ field }) => (
                  <Select {...field} placeholder="选择语言" options={AD_LANGUAGES} />
                )}
              />
            </Form.Item>

            <Form.Item
              label="传媒资源 (Media Source)"
              required
              validateStatus={errors.adset?.mediaSource ? "error" : ""}
              help={errors.adset?.mediaSource?.message}
            >
              <Controller
                name="adset.mediaSource"
                control={control}
                render={({ field }) => (
                  <Select {...field} placeholder="选择媒体来源" options={MEDIA_SOURCES} />
                )}
              />
            </Form.Item>

            <Form.Item
              label="路径类型 (OS)"
              required
              validateStatus={errors.adset?.os ? "error" : ""}
              help={errors.adset?.os?.message}
            >
              <Controller
                name="adset.os"
                control={control}
                render={({ field }) => (
                  <Select {...field} placeholder="选择路径类型" options={OS_TYPES} />
                )}
              />
            </Form.Item>

            <Form.Item
              label="投手 (Optimizer)"
              required
              validateStatus={errors.adset?.optimizer ? "error" : ""}
              help={errors.adset?.optimizer?.message}
            >
              <Controller
                name="adset.optimizer"
                control={control}
                render={({ field }) => (
                  <Select {...field} placeholder="选择投手" options={OPTIMIZERS} />
                )}
              />
            </Form.Item>

            <Form.Item
              label="日期 (Date)"
              required
              validateStatus={errors.adset?.date ? "error" : ""}
              help={errors.adset?.date?.message}
            >
              <Controller
                name="adset.date"
                control={control}
                render={({ field }) => (
                  <Input {...field} placeholder="输入日期 (如 1205 或 1000325)" />
                )}
              />
            </Form.Item>

            <Form.Item
              label="剧集ID (Drama ID)"
              required
              validateStatus={errors.adset?.dramaId ? "error" : ""}
              help={errors.adset?.dramaId?.message}
            >
              <Controller
                name="adset.dramaId"
                control={control}
                render={({ field }) => (
                  <Input {...field} placeholder="输入剧集ID (如 10000235)" />
                )}
              />
            </Form.Item>

            <Form.Item
              label="事件 (Event)"
              required
              validateStatus={errors.adset?.event ? "error" : ""}
              help={errors.adset?.event?.message}
            >
              <Controller
                name="adset.event"
                control={control}
                render={({ field }) => (
                  <Select {...field} placeholder="选择事件类型" options={OPTIMIZATION_TYPES} />
                )}
              />
            </Form.Item>

            <Form.Item
              label="其他 (Optional)"
              validateStatus={errors.adset?.optional ? "error" : ""}
              help={errors.adset?.optional?.message}
            >
              <Controller
                name="adset.optional"
                control={control}
                render={({ field }) => (
                  <Input {...field} placeholder="输入可选后缀 (如 v1, v2)" />
                )}
              />
            </Form.Item>
          </Space>
        </Card>

        {/* Ad 列表区域 */}
        <Card title="Ad 配置" className="w-full">
          <Space direction="vertical" className="w-full" size="large">
            {fields.map((field, index) => (
              <AdFormItem
                key={field.id}
                index={index}
                control={control}
                errors={errors}
                onRemove={() => handleRemoveAd(index)}
                canRemove={canRemove}
              />
            ))}

            {/* 增加 Ad 按钮放在最后一个 Ad 配置后面 */}
            <div className="flex justify-center pt-2">
              <Button
                type="dashed"
                icon={<PlusOutlined />}
                onClick={handleAddAd}
                disabled={!canAddMore}
                size="large"
                className="w-full max-w-md"
              >
                增加 Ad ({fields.length}/{MAX_AD_COUNT})
              </Button>
            </div>

            {errors.ads && typeof errors.ads === "object" && (
              <div className="text-red-500 text-sm">
                {errors.ads.message || "请检查 Ad 配置"}
              </div>
            )}
          </Space>
        </Card>

        {/* 提交按钮 */}
        <div className="flex justify-end">
          <Button type="primary" htmlType="submit" size="large">
            生成
          </Button>
        </div>
      </Space>
    </Form>
    </FormProvider>
  );
}

