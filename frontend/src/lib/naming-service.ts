/**
 * 前端命名生成服务
 * 用于在不连接后端的情况下生成广告组和广告命名
 */

// 广告组命名参数
export interface AdSetNameParams {
  country: string;
  language: string;
  mediaSource: string;
  os: string;
  optimizer: string;
  date: string;
  dramaId: string;
  event: string;
  optional?: string;
}

// 广告命名参数
export interface AdNameParams {
  dramaId: string;
  language: string;
  team: string;
  designer: string;
  date: string;
  creativeType: string;
  number?: string;
  optional?: string;
}

// Campaign 命名参数
export interface CampaignNameParams {
  country: string;
  mediaSource: string;
  mktType: string;
  targetType?: string;
  optimizationTypes: string;
  os: string;
  programCode: string;
  programShortner?: string;
  title: string;
  eventType?: string;
  userEmailPrefix: string;
  optionalCampaign?: string;
}

// 优化类型缩写映射
const getOptimizationAbbreviation = (optimizationType: string): string => {
  return optimizationType.toLowerCase() === "install" ? "i" : "e";
};

// 优化类型命名映射
const getOptimizationNaming = (optimizationType: string): string => {
  const mapping: Record<string, string> = {
    install: "install",
    watch: "watch",
    purchase: "purchase",
    subscription: "subs",
  };
  return mapping[optimizationType.toLowerCase()] || optimizationType.toLowerCase();
};

// 文本规范化（空格转下划线，转小写）
const normalizeForNaming = (text: string): string => {
  if (!text) return "";
  return text.trim().replace(/\s+/g, "_").toLowerCase();
};

/**
 * 生成 Campaign 名称
 * 格式: {国家}_{媒体}_{营销类型}_{目标类型}_{优化缩写}_{优化类型}_{系统}_{剧目代码}_{剧目简称}_{事件}_{cn}_{用户}_{可选}
 */
export const generateCampaignName = (params: CampaignNameParams): string => {
  const parts: string[] = [];

  // 必填字段
  parts.push(params.country);
  parts.push(params.mediaSource);
  parts.push(params.mktType);

  // 可选目标类型
  if (params.targetType) {
    parts.push(params.targetType);
  }

  // 优化类型缩写和命名
  parts.push(getOptimizationAbbreviation(params.optimizationTypes));
  parts.push(getOptimizationNaming(params.optimizationTypes));

  // OS
  parts.push(params.os);

  // 剧目代码
  parts.push(params.programCode);

  // 剧目简称（优先使用 shortner，否则使用 title）
  if (params.programShortner) {
    parts.push(params.programShortner.toLowerCase());
  } else {
    parts.push(normalizeForNaming(params.title));
  }

  // 可选事件类型
  if (params.eventType) {
    parts.push(params.eventType);
  }

  // 团队标识
  parts.push("cn");

  // 用户邮箱前缀
  if (params.userEmailPrefix) {
    parts.push(params.userEmailPrefix);
  }

  // 可选备注
  if (params.optionalCampaign) {
    parts.push(params.optionalCampaign);
  }

  return parts.join("_");
};

/**
 * 生成广告组名称 (新命名规则 v2)
 * 格式: app-vigloo_{国家}_{语言}_{媒体}_{系统}_{投手}_{日期}_{剧集ID}_{事件}_{可选}
 */
export const generateAdSetName = (params: AdSetNameParams): string => {
  const parts: string[] = ["app-vigloo"];

  // 必填字段
  parts.push(params.country.toLowerCase());
  parts.push(params.language.toLowerCase());
  parts.push(params.mediaSource.toLowerCase());
  parts.push(params.os.toLowerCase());
  parts.push(params.optimizer.toLowerCase());
  parts.push(params.date);
  parts.push(params.dramaId);
  parts.push(params.event.toLowerCase());

  // 可选后缀
  if (params.optional) {
    parts.push(params.optional.toLowerCase());
  }

  return parts.join("_");
};

/**
 * 生成广告名称 (新命名规则 v2)
 * 格式: {剧集ID}_{语言}_{团队}_{设计师}_{日期}_{素材类型}_{编号}_{可选}
 */
export const generateAdName = (params: AdNameParams): string => {
  const parts: string[] = [];

  // 必填字段
  parts.push(params.dramaId);
  parts.push(params.language.toLowerCase());
  parts.push(params.team.toLowerCase());
  parts.push(params.designer.toLowerCase());
  parts.push(params.date);
  parts.push(params.creativeType.toLowerCase());

  // 可选编号
  if (params.number) {
    parts.push(params.number);
  }

  // 可选后缀
  if (params.optional) {
    parts.push(params.optional.toLowerCase());
  }

  return parts.join("_");
};

/**
 * 批量生成广告名称
 */
export const generateAdNames = (ads: AdNameParams[]): string[] => {
  return ads.map((ad) => generateAdName(ad));
};

/**
 * 生成完整的命名结果
 */
export interface GenerationResult {
  campaignName: string;
  adSetName: string;
  adResults: Array<{
    adName: string;
    oneLinkUrl: string;
  }>;
}

export interface GenerateAllParams {
  campaign: CampaignNameParams;
  adset: AdSetNameParams;
  ads: AdNameParams[];
}

export const generateAll = (params: GenerateAllParams): GenerationResult => {
  const campaignName = generateCampaignName(params.campaign);
  const adSetName = generateAdSetName(params.adset);
  const adNames = generateAdNames(params.ads);

  // 生成 OneLink URL（简化版，实际需要更多参数）
  const adResults = adNames.map((adName) => ({
    adName,
    oneLinkUrl: `https://vigloo.onelink.me/abcd?c=${encodeURIComponent(campaignName)}&af_adset=${encodeURIComponent(adSetName)}&af_ad=${encodeURIComponent(adName)}`,
  }));

  return {
    campaignName,
    adSetName,
    adResults,
  };
};
