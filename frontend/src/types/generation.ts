// Generation API types

// 新命名规则 - 广告组
// 格式: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他}
export interface AdSetRequest {
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

// 新命名规则 - 广告
// 格式: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他}
export interface AdRequest {
  dramaId: string;
  language: string;
  team: string; // vc, vk, cj
  designer: string;
  date: string;
  creativeType: string;
  number?: string;
  optional?: string;
}

export interface GenerationRequest {
  programCode: string;
  adset: AdSetRequest;
  ads: AdRequest[];
}

export interface AdResult {
  adName: string;
}

export interface GenerationResponse {
  adSetName: string;
  adResults: AdResult[];
}
