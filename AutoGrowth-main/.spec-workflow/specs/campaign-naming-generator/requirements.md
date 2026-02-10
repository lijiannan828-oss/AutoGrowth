# 需求文档

## 项目信息

**规范名称**: campaign-naming-generator

**项目名称**: 短剧投放命名与链接自动化生成器

**创建日期**: 2025-01-11

**状态**: 待审批

## 概述

本文档定义了短剧投放命名与链接自动化生成器的功能需求。该工具旨在消除投手在创建广告系列时的手动命名和链接生成工作，通过自动化 SOP 规则应用，将设置时间从 10-15 分钟减少到 30 秒以内。

## 用户故事

### US-001: 用户登录与身份识别

**作为** 投手  
**我想要** 使用 Google 账号快捷登录系统  
**以便于** 系统能够识别我的身份并自动将我的邮箱前缀附加到生成的名称中，同时保证只有公司授权邮箱可以访问

**验收标准**:
- 登录方式为 Google Sign-In（Firebase Authentication）
- 仅允许白名单域名（例如 `@company.com`）或特定邮箱登录，其他账号拒绝访问
- 登录成功后获取用户邮箱，并成功提取邮箱前缀（@ 符号前部分）
- 登录状态持久化，用户刷新页面后仍保持登录状态
- 用户可以通过登出功能退出登录
- 未登录或白名单之外的用户访问生成页面时自动跳转到登录页或展示无权限提示

**优先级**: 高

---

### US-002: 剧目列表浏览与快速进入

**作为** 投手  
**我想要** 在进入系统后看到按上架时间排序的剧目列表，并在列表中直接进入配置流程  
**以便于** 快速选择今日要投放的剧目，避免额外搜索步骤

**验收标准**:
- 登录后默认展示完整剧目列表，按上架/更新时间倒序排序
- 列表至少显示以下字段：剧名、Program Code、Program shortner、上架时间、主要投放地区（如有）、状态标签
- 每条剧目行提供“去创建广告”行动按钮，点击后进入策略配置表单并带入剧目信息
- 列表支持分页或无限滚动（根据数据量），保证性能
- 支持在列表上方显示今日新增或推荐剧目的提示区块
- 列表在桌面和移动端均具备良好可读性

**优先级**: 高

---

### US-003: 剧目信息搜索与自动完成

**作为** 投手  
**我想要** 通过输入 Program Code 或 Title 搜索剧目信息，并在列表中定位结果  
**以便于** 快速找到目标剧目并立即进入配置

**验收标准**:
- 用户可以通过 Program Code（如 "KR000P05S01"）搜索
- 用户可以通过 Title（如 "Romantic Island"）搜索
- 搜索框与剧目列表联动：输入关键词时只展示匹配剧目，并高亮匹配字段
- 搜索结果与“去创建广告”按钮共存，点击按钮后进入策略配置页面
- 搜索响应时间 < 500ms（考虑缓存）
- 支持模糊匹配和部分匹配

**优先级**: 高

---

### US-004: 统一策略配置表单输入

**作为** 投手  
**我想要** 在一个页面上完成 Campaign、Ad Set、Ad 的所有策略配置  
**以便于** 系统能够生成符合 SOP 规则的 Campaign Name、Ad Set Name 和多个 Ad Name

**验收标准**:
- **广告系列级别字段**（在同一页面）：
  - Country（国家，下拉框，选项：Worldwide-ww, United States-us, Japan-jp, South Korea-kr, Indonesia-id, Thailand-th；移除 Vietnam-vn、Philippines-ph）
    - 选择 Worldwide 时，命名中的 Country 段使用 'ww'
  - Media source（媒体来源，下拉框，选项：Facebook (fb)、TikTok (tt)、Google (go)、Snapchat (sc)、Pangle (pg)，默认 Facebook (fb)）
  - Mkt type（市场类型，下拉框，选项：UA (ua)、Branding (branding)，默认 UA (ua)）
  - Target type（目标类型，下拉框，选项：Auto (auto)，默认不填）
  - Optimization types（优化类型，下拉框，选项：Install (install)、Watch (watch)、Purchase (purchase)、Subscription (subscription)）
  - OS（操作系统，下拉框，如 w2a, os, and, ios）
  - Event type（事件类型，文本输入，选填，placeholder："如果有投其他事件，就填写其他事件参数"）
  - Optional (Campaign)（可选备注，文本输入，选填，如 'han'）
  - Logged In User（当前登录用户的邮箱前缀，只读显示）
- **广告组级别字段**（在同一页面）：
  - Optional (Ad Set)（文本输入，必填，用于区分不同的广告组变体，如 "test01"）
- **广告级别字段**（支持多个Ad，动态添加）：
  - 初始显示一个 Ad 表单
  - 提供"增加 Ad"按钮，点击后可添加新的 Ad 表单
  - 最多支持添加 30 个 Ad
  - 每个 Ad 表单包含以下字段：
    - creative type（创意类型，下拉框，选项：Highlight、Teaser、Episode）
    - Number（编号，数字输入，当 creative type='highlight' 时必填，当 creative type='epi' 时可选，占位符：Highlight-"混剪素材的片段是取自第几集，如果是多集混剪，填写其中一集"，Episode-"原片素材取自第几集（可选）"）
    - Intro Ep No（介绍集数，数字输入，当 creative type='highlight' 时必填，当 creative type='epi' 时可选，占位符：Highlight-"混剪素材的片头是取自第几集"，Episode-"片头素材取自第几集（可选）"）
    - Text included（包含文本，复选框，选中时值为 'txt'）
    - concept keyword（概念关键词，文本输入，选填，如 "kiss"）
    - Ad Language（Ad 语言，下拉框，选项：English-en, Korean-kr, Japan-jp, Thailand-th, Indonesian-id，用于 Ad 命名）
    - Onelink Intro Ep No（Onelink 介绍集数，数字输入，必填，默认值为 1，底纹词："onelink落地页从第几集开始播放"）
    - Onelink Language（Onelink 语言，下拉框，必填，底纹词："onelink落地页语言"，选项：English-en, Korean-ko, Japanese-ja, Indonesian-id, Chinese-zh，用于 OneLink URL 生成，默认值与 Ad Language 联动）
  - 每个 Ad 表单提供删除按钮（至少保留一个 Ad）
  - 条件字段显示/隐藏逻辑：
    - 当 creative type='highlight' 时，Number 和 Intro Ep No 字段显示且必填（必须是数字）
    - 当 creative type='epi' 时，Number 和 Intro Ep No 字段显示但不必填（如果填写，必须是数字）
    - 当 creative type 不等于 'highlight' 且不等于 'epi' 时，Number 和 Intro Ep No 字段隐藏
    - Onelink Intro Ep No 字段始终显示且必填（默认值为 1）
    - Ad Language 和 Onelink Language 字段始终显示且必填
    - Onelink Language 默认值与 Ad Language 联动：
      - Ad Language (en) -> Onelink Language (en)
      - Ad Language (kr) -> Onelink Language (ko)
      - Ad Language (jp) -> Onelink Language (ja)
      - Ad Language (id) -> Onelink Language (id)
      - Ad Language (th) -> Onelink Language (en)（Thailand 联动到 English，不是 Chinese）
      - 其他 -> Onelink Language (en)
- 所有字段在同一页面按逻辑分组展示（Campaign 区域、Ad Set 区域、Ad 列表区域）
- 所有必填字段有明确标识
- 表单验证实时反馈错误信息
- 支持表单整体提交验证

**优先级**: 高

---

### US-007: Campaign Name 自动生成

**作为** 投手  
**我想要** 系统按照 SOP 规则自动生成 Campaign Name  
**以便于** 确保名称符合规范且无需手动拼接

**验收标准**:
- Campaign Name 格式严格按照以下顺序用下划线拼接：
  `[Country]_[Media source]_[Mkt type]_[Target type]_[Optimization abbreviation]_[Optimization types]_[OS]_[Program code]_[Program shortner/Title]_[Event type]_cn_[User email prefix]_[Optional (Campaign)]`
- **Program Code**: 从 Google Sheets 的 Program Info 表中自动获取（用户选择剧目后自动带入）
- **Program Shortener**: 根据 Program Code 在 Google Sheets 的 "Shortener" sheet 的 "Title (Shortner)" 字段中自动匹配获取；如果未匹配到，则使用 "En" sheet 的 "Title" 字段作为兜底（空格转换为下划线，并转换为小写）
- **'cn' 团队归属标识**: 在 User email prefix 之前添加 'cn' 表示团队归属
- Optimization abbreviation 根据 Optimization types 自动判断（无需用户填写）：
  - install → 'i'
  - watch → 'e'
  - purchase → 'e'
  - subscription → 'e'
- Optimization types 在命名中的格式：
  - subscription → 'subs'
  - 其他类型保持原值（install, watch, purchase）
- 空字段智能跳过（不添加下划线）
- **'cn' 团队归属标识**: 在 User email prefix 之前添加 'cn' 表示团队归属
- 用户邮箱前缀：如果系统获取到登录用户，则自动附加在 'cn' 之后、Optional (Campaign) 之前；如果未获取到登录用户，则不包含此字段（但 'cn' 仍会保留）
- 生成的名称保证符合 SOP 标准，无格式错误

**优先级**: 高

---

### US-008: Ad Set Name 自动生成

**作为** 投手  
**我想要** 系统基于 Campaign Name 自动生成 Ad Set Name  
**以便于** 确保广告组名称与广告系列名称关联且符合规范

**验收标准**:
- Ad Set Name 格式：`[Generated Campaign Name]_[Optional (Ad Set)]`
- 基于已生成的 Campaign Name 进行拼接
- 确保 Ad Set Name 与 Campaign Name 不完全相同（因为 Optional (Ad Set) 必填）
- 生成的名称保证符合 SOP 标准

**优先级**: 高

---

### US-009: Ad Name 批量自动生成

**作为** 投手  
**我想要** 系统按照 SOP 规则为每个配置的 Ad 自动生成 Ad Name  
**以便于** 确保所有广告名称符合规范且智能处理可选字段

**验收标准**:
- 系统为表单中配置的每个 Ad 生成一个独立的 Ad Name
- Ad Name 格式严格按照以下顺序用下划线拼接：
  `video_[Program code]_[Title(EN/Shortener)]_[creative type]_[Number]_[Intro Ep No]_[Text included]_[concept keyword_intro]_[Ad Language]_cn_[User email prefix]`
- **Program Code**: 从 Google Sheets 的 Program Info 表中自动获取（用户选择剧目后自动带入）
- **Title(EN/Shortener)**: 优先从 Google Sheets 的 "Shortener" sheet 的 "Title (Shortner)" 字段中根据 Program Code 自动匹配获取，如果该字段不存在或为空，则默认使用 "En" sheet 的 "Title" 字段（空格转换为下划线，并转换为小写）
- 固定前缀 "video"
- **Creative Type**: 选项为 Highlight、Teaser、Episode，对应命名中分别为 'highlight'、'teaser'、'epi'
- 条件字段智能跳过：
  - Number: 仅当 creative type='highlight' 或 'epi' 时包含（highlight 必填，epi 可选），否则跳过
  - Intro Ep No: 仅当 creative type='highlight' 或 'epi' 时包含（highlight 必填，epi 可选），否则跳过
  - Text included: 如果为 true，值为 'txt'，否则跳过（包括下划线）
  - concept keyword: 如果为空，跳过（包括下划线和 "_intro" 后缀）
- **Ad Language**: 选项为 English-en, Korean-kr, Japan-jp, Thailand-th, Indonesian-id，对应命名中分别为 'en'、'kr'、'jp'、'th'、'id'（用于 Ad 命名）
- **'cn' 团队归属标识**: 在 User email prefix 之前添加 'cn' 表示团队归属（仅一个 'cn'，无固定后缀）
- 用户邮箱前缀：如果系统获取到登录用户，则自动附加在 'cn' 之后；如果未获取到登录用户，则不包含此字段（但 'cn' 仍会保留）
- **重要**: Title(EN/Shortener) 中的所有空格必须转换为下划线，并转换为小写，确保生成的名称中每个单词间都是下划线分隔且为小写
- 生成的名称保证符合 SOP 标准
- 生成的 Ad Name 数量必须与表单中配置的 Ad 数量一致（最多 30 个）

**优先级**: 高

---

### US-010: OneLink URL 批量自动生成

**作为** 投手  
**我想要** 系统为每个 Ad 自动生成对应的完整 OneLink URL  
**以便于** 直接使用生成的链接进行广告投放

**验收标准**:
- 系统为表单中配置的每个 Ad 生成一个独立的 OneLink URL
- OneLink URL 基础地址固定为 `https://vigloo.onelink.me/SrIM`
- 每个 OneLink URL 包含以下参数（并全部经过 URL 编码处理）：
  - `pid`: 根据媒体来源（Media source）映射到指定值：
  - fb (Facebook) → metaweb_int
  - tt (TikTok) → tiktok_int
  - go (Google) → google_int
  - sc (Snapchat) → snapchat_int
  - pg (Pangle) → pangle_int
  - `c`: Generated Campaign Name（所有 Ad 共享）
  - `af_adset`: Generated Ad Set Name（所有 Ad 共享）
  - `af_ad`: 对应 Ad 的 Generated Ad Name（每个 Ad 使用各自的 Ad Name）
  - `programId`: 从 Program Info 获取，具体来源为 Google Sheets "All" sheet 的 "id" 字段（所有 Ad 共享）
  - `seasonId`: 从 Program Info 获取，具体来源为 Google Sheets "All" sheet 的 "seasonId" 字段（如存在，所有 Ad 共享）
  - `deep_link_sub1`: Program ID（需要追加两次，保持与 SOP 一致，所有 Ad 共享），值同 `programId`，来源为 Google Sheets "All" sheet 的 "id" 字段
  - `deep_link_sub2`: Season ID（所有 Ad 共享）
  - `deep_link_sub3`: Episode Number（来源于对应 Ad 的表单字段 Onelink Intro Ep No，每个 Ad 使用各自的 Onelink Intro Ep No）
  - `af_web_dp`: `https://www.vigloo.com/{onelinkLanguage}/video/{programId}?episode={episodeNumber}`（每个 Ad 使用各自的 Onelink Language 和 Onelink Intro Ep No，其中 `programId` 来自 Google Sheets "All" sheet 的 "id" 字段，`episodeNumber` 使用 Onelink Intro Ep No，`onelinkLanguage` 使用 Onelink Language 字段的值，映射规则：English-en, Korean-ko, Japanese-ja, Indonesian-id, Chinese-zh）
  - `af_force_deeplink`: 固定值 `true`
  - `is_retargeting`: 固定值 `true`
  - `af_dp`: `vigloo%3A%2F%2Fdeeplink%2Fprogram%3FprogramId%3D{programId}%26seasonId%3D{seasonId}%26episodeNumber%3D{episodeNumber}`（整体编码后的深度链接 URI，每个 Ad 使用各自的 Onelink Intro Ep No 作为 `episodeNumber`，其中 `programId` 来自 Google Sheets "All" sheet 的 "id" 字段，`seasonId` 来自 Google Sheets "All" sheet 的 "seasonId" 字段）
  - `af_reengagement_window`: 固定值 `7d`
  - `af_inactivity_window`: 固定值 `7d`
  - `af_click_lookback`: 固定值 `7d`
  - `deep_link_value`: 固定值 `program`
- 系统根据每个 Ad 的表单输入的 Onelink Language 字段和 Onelink Intro Ep No 生成 OneLink URL 相关参数（所有使用 Episode Number 的地方都使用 Onelink Intro Ep No，所有使用 Language 的地方都使用 Onelink Language）
- Onelink Language 映射规则（用于 OneLink URL）：English-en, Korean-ko, Japanese-ja, Indonesian-id, Chinese-zh（与 Ad Language 的映射规则不同）
- 生成的 URL 格式正确、参数完整，可直接使用
- 生成的 OneLink URL 数量必须与生成的 Ad Name 数量完全一致（最多 30 个）
- 支持从配置或 Program Info 中扩展额外固定参数

**优先级**: 高

---

### US-011: 生成结果展示与复制

**作为** 投手  
**我想要** 查看生成的所有结果并逐条复制  
**以便于** 快速将结果应用到广告平台

**验收标准**:
- 系统显示以下生成结果：
  - Campaign Name（1个）
  - Ad Set Name（1个）
  - Ad Name（多个，数量与用户添加的 Ad 数量一致）
  - OneLink URL（多个，数量与 Ad Name 数量一致，每个 OneLink URL 对应一个 Ad Name）
- 结果展示格式：
  - Campaign Name 和 Ad Set Name 各显示在一个独立的结果卡片中
  - Ad Name 和对应的 OneLink URL 成对显示（每个 Ad 对应一个结果卡片，包含 Ad Name 和对应的 OneLink URL）
  - 所有结果卡片按顺序排列，清晰标识每个结果的类型
- 每个结果都有独立的复制按钮
- 点击复制按钮后，内容自动复制到剪贴板
- 复制成功后显示视觉反馈（如 Toast 提示或按钮状态变化）
- 结果以清晰易读的格式展示（如卡片或列表）
- 支持滚动查看所有结果
- OneLink URL 的数量必须与 Ad Name 的数量完全一致

**优先级**: 高

---

### US-012: 表单验证与错误提示

**作为** 投手  
**我想要** 在输入错误时得到清晰的提示  
**以便于** 快速修正错误并成功生成结果

**验收标准**:
- 所有必填字段在提交前进行验证
- 条件必填字段（如 creative type='highlight' 时的 Number 和 Intro Ep No）根据条件进行验证
- Onelink Intro Ep No 始终必填，默认值为 1
- 验证错误实时显示在对应字段下方
- 错误提示信息清晰明确，说明如何修正
- 提交按钮在表单无效时禁用
- 支持字段级别的验证（输入时实时检查）

**优先级**: 中

---

### US-013: 数据缓存与性能优化

**作为** 投手  
**我想要** 系统快速响应我的操作  
**以便于** 提高工作效率

**验收标准**:
- 剧目搜索响应时间 < 500ms（利用缓存）
- 生成操作响应时间 < 1s
- Program Info 数据缓存策略：
  - 首次访问时从 Google Sheets 读取
  - 缓存到 Cloud SQL 或 Redis（TTL 5 分钟）
  - 缓存命中时直接返回，无需调用 Google Sheets API
- Google Sheets API 限流时自动回退到缓存数据
- 前端使用 React Query 缓存最近查询结果

**优先级**: 中

---

### US-014: 生成历史记录（可选）

**作为** 投手  
**我想要** 查看我之前的生成记录  
**以便于** 参考历史配置或重复使用

**验收标准**:
- 系统保存每次生成的完整记录到 Cloud SQL
- 记录包含：
  - 用户邮箱前缀
  - Program Code
  - 所有输入字段
  - 生成的 4 个结果
  - 生成时间
- 用户可以在历史记录页面查看自己的记录
- 支持按时间、Program Code 筛选
- 支持从历史记录快速重新生成（预填充表单）

**优先级**: 低

---

## 非功能需求

### NFR-001: 性能需求
- 页面首次加载时间 < 2s
- API 响应时间 < 1s（95 百分位）
- 支持至少 50 个并发用户

### NFR-002: 可用性需求
- 系统可用性 > 99.5%（月度）
- 支持 7x24 小时访问
- 错误恢复时间 < 5 分钟

### NFR-003: 安全需求
- 所有 API 通信使用 HTTPS
- Firebase Authentication ID Token 必须在后端校验（使用 Firebase Admin SDK 或 Google 公钥）
- 仅允许配置的白名单邮箱或域名通过校验
- JWT/Session（若有）设置合理的过期时间（24 小时）
- 敏感信息（服务账号凭证、白名单配置）存储在 Google Secret Manager
- 实现 API 请求频率限制，防止滥用

### NFR-004: 兼容性需求
- 支持主流浏览器：Chrome、Firefox、Safari、Edge（最新 2 个版本）
- 响应式设计，支持桌面和移动设备访问
- 前端适配不同屏幕尺寸

### NFR-005: 可维护性需求
- 代码遵循 TypeScript/Python 最佳实践
- 关键业务逻辑有单元测试覆盖
- API 文档自动生成（FastAPI 自动文档）
- 日志记录关键操作和错误

## 数据需求

### DR-001: Program Info 表结构
系统需要从 Google Sheets Program Info 表读取以下字段：
- **programCode**（主键，来源：All sheet 的 "ProgramCode" 列）
- **title**（来源：En sheet 的 "Title" 列，通过 ProgramCode 匹配）
- **programId**（来源：All sheet 的 "id" 列）
- **seasonId**（来源：All sheet 的 "seasonId" 列，如存在）
- **programShortner**（来源：Shortener sheet 的 "Title (Shortner)" 列，根据 ProgramCode 自动匹配）
- **titleENShortener**（来源：Shortener sheet 的 "Title (Shortner)" 列，如果不存在或为空则使用 En sheet 的 "Title" 字段，用于 Ad Name 生成）
- **baseOneLinkUrl**（如有覆盖，默认为 `https://vigloo.onelink.me/SrIM`）
- **fixedParams**（JSON 格式的固定参数，包含 `af_force_deeplink`、`is_retargeting` 等默认值）

**重要说明**:
- Program Shortener 和 Title(EN/Shortener) 都从 "Shortener" sheet 的 "Title (Shortner)" 字段获取（注意字段名拼写为 Shortner）
- 根据 Program Code 在 "Shortener" sheet 中匹配对应的 "Title (Shortner)" 值
- 如果 "Title (Shortner)" 字段不存在或为空，Title(EN/Shortener) 将使用 "En" sheet 的 "Title" 作为默认值
- Title(EN/Shortener) 在用于命名生成时，所有空格必须转换为下划线

### DR-001.1: 媒体来源 PID 映射
系统需要维护媒体来源（Media source）到 pid 的映射表，可来源于配置文件或 Program Info 附加字段，例如：
- fb (Facebook) → metaweb_int
- tt (TikTok) → tiktok_int
- go (Google) → google_int
- sc (Snapchat) → snapchat_int
- pg (Pangle) → pangle_int

### DR-001.2: Episode Number 字段映射
系统需要明确 Episode Number 来源字段（例如表单中的 Intro Ep No），并在 OneLink 生成时使用该值作为 `deep_link_sub3` 和 `episodeNumber`。

### DR-002: 登录白名单配置
系统需要持久化或配置以下信息：
- 允许登录的邮箱域名列表（如 `@company.com`）
- 如需针对个人邮箱授权，需维护白名单邮箱列表
- 白名单可存储在 Cloud SQL、Firestore 或配置文件中，并通过环境变量/Secret 注入

### DR-003: 用户数据存储
系统需要在 Cloud SQL PostgreSQL 中存储：
- 用户邮箱
- 邮箱前缀
- 登录时间
- 生成历史记录（可选）

### DR-004: 剧目列表数据需求
系统需要提供用于列表展示的额外字段：
- 剧目上线时间或更新时间（用于倒序排列）
- 剧目封面/缩略图（可选）
- 推荐标记（如“今日上线”“热门”）
- 状态字段（如上线中、待上线）

## 集成需求

### INT-001: Google Sheets API 集成
- 使用服务账号认证访问 Google Sheets
- 实现数据读取和缓存机制
- 处理 API 限流和错误情况

### INT-002: Cloud SQL 集成
- 使用 SQLAlchemy + asyncpg 连接 PostgreSQL
- 实现用户数据存储和查询
- 实现生成历史记录存储（可选）

### INT-003: Firebase Authentication 集成
- 前端集成 Firebase Authentication（Google Provider）实现一键登录
- 后端使用 Firebase Admin SDK 或 Google 公钥验证 ID Token 的合法性与有效期
- 登录成功后校验邮箱是否在白名单内
- 处理 Token 过期与刷新流程

### INT-004: Firebase Hosting 集成
- 前端部署到 Firebase Hosting
- 配置自定义域名和 HTTPS
- 实现 CI/CD 自动部署

### INT-005: Cloud Run 集成
- 后端部署到 Cloud Run
- 配置自动扩缩容
- 实现健康检查和监控

### INT-006: 剧目列表 API 集成
- 后端提供获取完整剧目列表的接口，支持排序、分页、过滤
- 接口支持按上线时间倒序排序
- 支持根据搜索关键字返回过滤后的剧目
- 支持将推荐标记、状态信息返回给前端

## 约束条件

### C-001: 技术约束
- 前端必须使用 Next.js 14 + TypeScript
- 后端必须使用 FastAPI + Python 3.11
- 数据源必须从 Google Sheets Program Info 表读取
- 必须使用 GCP 服务（Firebase Hosting、Cloud Run、Cloud SQL）

### C-002: 业务约束
- SOP 命名规则是固定的，不能更改
- OneLink 模板格式是固定的
- 用户邮箱前缀格式必须统一（@ 符号前部分）

### C-003: 运营约束
- Google Sheets Program Info 表由运营团队维护
- 系统需要处理 Google Sheets API 的访问限制
- 系统需要支持数据更新后的实时或准实时同步

## 假设条件

### A-001: 用户假设
- 用户拥有白名单内的 Google 邮箱账号
- 用户理解广告系列的基本概念和字段含义
- 用户能够访问 Web 浏览器

### A-002: 数据假设
- Google Sheets Program Info 表定期准确更新
- 表结构保持稳定，不会频繁变更
- 服务账号具有读取权限

### A-003: 基础设施假设
- GCP 基础设施可用且稳定
- 网络连接稳定
- 服务账号凭证已配置

## 验收测试场景

### TC-001: 完整生成流程
1. 用户登录系统
2. 搜索并选择剧目 "KR000P05S01"
3. 在统一表单页面填写 Campaign、Ad Set 字段
4. 添加多个 Ad（例如 3 个），为每个 Ad 填写相应字段
5. 点击生成按钮
6. 验证生成的结果：
   - 1 个 Campaign Name
   - 1 个 Ad Set Name
   - 3 个 Ad Name（与添加的 Ad 数量一致）
   - 3 个 OneLink URL（与 Ad Name 数量一致，每个对应一个 Ad）
7. 验证所有结果符合 SOP 规则
8. 验证邮箱前缀正确附加
9. 验证 OneLink URL 格式正确
10. 逐条复制所有结果
11. 验证复制功能正常工作

### TC-002: 条件字段验证
1. 选择 creative type = 'highlight'
2. 验证 Number 和 Intro Ep No 字段显示且必填
3. 验证 Onelink Intro Ep No 字段显示且必填（默认值为 1）
4. 选择 creative type = 'epi'
5. 验证 Number 和 Intro Ep No 字段显示但不必填（底纹词包含"可选"）
6. 验证 Onelink Intro Ep No 字段显示且必填（默认值为 1）
7. 选择 creative type = 'teaser'
8. 验证 Number 和 Intro Ep No 字段隐藏
9. 验证 Onelink Intro Ep No 字段显示且必填（默认值为 1）

### TC-003: 缓存机制验证
1. 首次搜索剧目，验证从 Google Sheets 读取
2. 5 分钟内再次搜索相同剧目，验证从缓存读取
3. 验证响应时间差异

## 依赖关系

### 外部依赖
- Google Sheets API
- Google Cloud Platform 服务
- Firebase Hosting
- Cloud Run
- Cloud SQL for PostgreSQL

### 内部依赖
- 用户认证系统
- 数据缓存系统
- 命名规则引擎
- OneLink 生成引擎

## 待定事项

### TBD-001: Optimization abbreviation 完整映射表（已确认）
已确认所有 Optimization types 到 abbreviation 的映射关系：
- install → 'i'
- watch → 'e'
- purchase → 'e'
- subscription → 'e'
- subscription 在命名中缩写为 'subs'

### TBD-002: OneLink 固定参数列表
需要确认 Program Info 表中 fixedParams 的具体格式和所有固定参数。

### TBD-003: 用户认证方式
- 已确定使用 Firebase Authentication（Google Sign-In）+ 白名单策略

### TBD-004: 错误处理策略
需要确认 Google Sheets API 失败时的降级策略。

### TBD-005: 剧目推荐规则
需要确认列表中"今日推荐"或"热门"标签的判定逻辑与数据来源。

---

### US-010: Program Info 数据库存储与同步

**作为** 系统管理员  
**我想要** 将 Google Sheets 中的 Program Info 数据同步到 Cloud SQL 数据库，并设置定时同步任务  
**以便于** 提高数据访问性能，减少对 Google Sheets API 的依赖，并确保数据一致性

**验收标准**:
- 在 `auto_growth` 数据库中创建 `program_info` 表
- 表字段设计与 Google Sheets 中的字段完全一致，包括：
  - `program_code` (主键)
  - `program_id`
  - `title`
  - `sub_title`
  - `synopsis`
  - `episode_count`
  - `release_date`
  - `content_information`
  - `program_shortner`
  - `title_en_shortener`
  - `season_id`
  - `created_at` (记录创建时间)
  - `updated_at` (记录更新时间)
- 实现数据同步服务，能够从 Google Sheets 读取数据并写入数据库
- 实现变更检测机制，只更新有变化的记录
- 设置定时任务，在北京时间每天 9:00、12:00、18:00 自动执行同步
- 所有直接读取 Google Sheets 的代码改为从数据库读取
- 提供手动触发同步的接口（用于测试和紧急同步）
- 首次同步完成后，前端能够正常显示数据

**优先级**: 高

**技术约束**:
- 使用 APScheduler 或 Cloud Scheduler 实现定时任务
- 时区设置为 Asia/Shanghai (UTC+8)
- 同步过程需要记录日志，便于排查问题
- 数据库操作使用 SQLAlchemy ORM

---

## 变更历史

| 日期 | 版本 | 变更说明 | 变更人 |
|------|------|----------|--------|
| 2025-01-11 | 1.0 | 初始版本 | AI Assistant |
| 2025-01-11 | 1.1 | 添加 US-010: Program Info 数据库存储与同步需求 | AI Assistant |

