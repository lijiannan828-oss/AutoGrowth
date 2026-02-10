import { z } from "zod";

// 新命名规则 - 广告 Schema
// 格式: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他}
export const adSchema = z.object({
  dramaId: z.string().min(1, "请输入戏剧ID"),
  language: z.string().min(1, "请选择语言"),
  team: z.string().min(1, "请选择团队"),
  designer: z.string().min(1, "请选择设计师"),
  date: z.string().min(1, "请输入日期 (MMDD格式)"),
  creativeType: z.string().min(1, "请选择创意类型"),
  number: z.string().optional(),
  optional: z.string().optional(),
});

export const adSchemaWithCondition = adSchema.superRefine((data, ctx) => {
  // 验证日期格式 (MMDD 或数字)
  if (data.date && !/^\d{4,6}$/.test(data.date.trim())) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "日期格式应为 MMDD (如 1205)",
      path: ["date"],
    });
  }
});

// 新命名规则 - 广告组 Schema
// 格式: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他}
export const adsetSchema = z.object({
  country: z.string().min(1, "请选择国家"),
  language: z.string().min(1, "请选择语言"),
  mediaSource: z.string().min(1, "请选择媒体来源"),
  os: z.string().min(1, "请选择路径类型"),
  optimizer: z.string().min(1, "请选择投手"),
  date: z.string().min(1, "请输入日期"),
  dramaId: z.string().min(1, "请输入剧集ID"),
  event: z.string().min(1, "请选择事件类型"),
  optional: z.string().optional(),
});

export const strategyFormSchema = z.object({
  // 新命名规则 - 广告组
  adset: adsetSchema,
  // 新命名规则 - 广告
  ads: z.array(adSchemaWithCondition).min(1, "至少需要一个 Ad"),
});
