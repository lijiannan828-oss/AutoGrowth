# 设计文档

## 项目信息

**规范名称**: campaign-naming-generator

**项目名称**: 短剧投放命名与链接自动化生成器

**创建日期**: 2025-01-11

**状态**: 待审批

**依赖文档**: requirements.md

## 概述

本文档定义了短剧投放命名与链接自动化生成器的技术设计方案，包括系统架构、模块设计、数据模型、API 设计、UI/UX 设计等。

## 系统架构设计

### 整体架构

系统采用前后端分离架构：

```
┌─────────────────────┐
│   用户浏览器         │
│  (Next.js Frontend) │
└──────────┬──────────┘
           │ HTTPS
           │
┌──────────▼──────────┐
│  Firebase Hosting    │
│  (静态资源托管)      │
└──────────┬──────────┘
           │ HTTPS API 调用
           │
┌──────────▼──────────┐        ┌─────────────────────┐
│   Cloud Run         │◀──────▶│  Cloud SQL          │
│  (FastAPI Backend)  │        │  (PostgreSQL)       │
└──────────┬──────────┘        └─────────────────────┘
           │
           │ Google Sheets API
           │
┌──────────▼──────────┐
│  Google Sheets      │
│  (Program Info)     │
└─────────────────────┘
```

### 技术栈

**前端**:
- Next.js 14 (App Router)
- TypeScript 5+
- Ant Design + Tailwind CSS
- React Hook Form + Zod
- React Query
- Axios

**后端**:
- FastAPI
- Python 3.11
- SQLAlchemy + asyncpg
- Google Sheets API Client
- PyJWT

**基础设施**:
- Firebase Hosting
- Cloud Run
- Cloud SQL for PostgreSQL
- Google Secret Manager

## 前端设计

### 页面结构

#### 登录页面 (`/login`)
- 显示 “使用 Google 登录” 按钮（Firebase Authentication）
- 展示白名单限制提示（若用户尝试使用非授权邮箱）
- 登录成功后跳转到生成页面

#### 生成页面 (`/`)
- **步骤指示区**：顶部展示“三步流程”导航（①选择剧目 ②填写策略 ③复制结果），高亮当前步骤
- **步骤 1：剧目列表区**
  - 显示按上线时间倒序的剧目列表（表格或卡片视图）
  - 提供搜索框、筛选条件、推荐剧集提示
  - 每条剧目提供“去创建广告”按钮，选中后进入步骤 2
- **步骤 2：策略配置区**
  - 展示当前选中剧目的摘要信息
  - 显示 Campaign、Ad Set、Ad 表单，按卡片或分组排列
  - 支持返回步骤 1 重新选择剧目
- **步骤 3：结果展示区**
  - 显示生成的 Campaign/Ad Set/Ad 名称及 OneLink URL
  - 提供一键复制按钮
  - 展示生成状态提醒与下一步提示
- 底部保留系统提示、版本信息等

### 组件设计

#### 1. ProgramSearch 组件
**位置**: `frontend/components/forms/ProgramSearch.tsx`

**功能**:
- 提供搜索输入框（支持 Program Code 或 Title）
- 显示自动完成下拉列表
- 选择后触发数据加载

**Props**:
```typescript
interface ProgramSearchProps {
  onSelect: (program: ProgramInfo) => void;
  value?: string;
}
```

**状态管理**:
- 使用 React Query 的 `useQuery` 调用 `/api/data/programs`
- 实现防抖（debounce）搜索
- 缓存搜索结果

#### 2. ProgramList 组件
**位置**: `frontend/components/programs/ProgramList.tsx`

**功能**:
- 展示按上线时间倒序的剧目列表
- 支持分页或无限滚动
- 支持搜索结果高亮、推荐标签展示、状态展示
- 提供“去创建广告”按钮和“查看详情”操作（可选）

**Props**:
```typescript
interface ProgramListProps {
  data: ProgramInfo[];
  isLoading: boolean;
  onSelect: (program: ProgramInfo) => void;
  pagination: { current: number; pageSize: number; total: number; };
}
```

**子组件**:
- ProgramCard / ProgramRow：在卡片或表格模式下渲染剧目
- ProgramHighlightTag：显示“今日上新”“热门”等标记

#### 3. ProgramSummary 组件
**位置**: `frontend/components/programs/ProgramSummary.tsx`

**功能**:
- 在策略配置区显示当前选中剧目的关键信息
- 提供“返回列表”或“重新选择”按钮

#### 4. StrategyForm 组件（统一策略配置表单）
**位置**: `frontend/components/forms/StrategyForm.tsx`

**功能**:
- 在一个页面中收集 Campaign、Ad Set、Ad 的所有字段
- 支持动态添加多个 Ad（最多 30 个）
- 实时验证
- 显示 Logged In User（只读）

**表单结构**:
- **Campaign 区域**:
    - Country (Select, 选项：Worldwide-ww, United States-us, Japan-jp, South Korea-kr, Indonesia-id, Thailand-th；移除 Vietnam、Philippines)
      - 命名规则中 Country 段直接使用所选值；当选择 Worldwide 时使用 'ww'
  - Media source (Select)
  - Mkt type (Select, 默认 'ua')
  - Target type (Select, 可选)
  - Optimization types (Select)
  - OS (Select)
  - Event type (Input, 可选)
  - Optional (Campaign) (Input, 可选)
  - Logged In User (Display only)
- **Ad Set 区域**:
  - Optional (Ad Set) (Input, 必填)
- **Ad 列表区域**:
  - 初始显示一个 Ad 表单
  - "增加 Ad" 按钮（最多 30 个）
  - 每个 Ad 表单包含：
    - creative type (Select)
    - Number (Input, 条件必填/可选，数字类型，占位符：Highlight-"混剪素材的片段是取自第几集，如果是多集混剪，填写其中一集"，Episode-"原片素材取自第几集（可选）")
    - Intro Ep No (Input, 条件必填/可选，数字类型，占位符：Highlight-"混剪素材的片头是取自第几集"，Episode-"片头素材取自第几集（可选）")
    - Text included (Checkbox)
    - concept keyword (Input, 可选)
    - Ad Language (Select, 选项：English-en, Korean-kr, Japan-jp, Thailand-th, Indonesian-id，用于 Ad 命名)
    - Onelink Intro Ep No (Input, 必填，数字类型，默认值 1，占位符："onelink落地页从第几集开始播放")
    - Onelink Language (Select, 必填，选项：English-en, Korean-ko, Japanese-ja, Indonesian-id, Chinese-zh，占位符："onelink落地页语言"，用于 OneLink URL 生成，默认值与 Ad Language 联动)
    - 删除按钮（至少保留一个 Ad）

**条件逻辑**:
```typescript
const showNumberFields = watch('ads[${index}].creativeType') === 'highlight' || watch('ads[${index}].creativeType') === 'epi';
const isNumberFieldsRequired = watch('ads[${index}].creativeType') === 'highlight';
// For highlight: Number and Intro Ep No are required
// For epi: Number and Intro Ep No are optional (displayed but not required)
// Onelink Intro Ep No is always required (default: "1")
```

**验证规则**:
- 当 creative type='highlight' 时，Number 和 Intro Ep No 必须为数字（使用正则表达式 `/^\d+$/` 验证）
- 当 creative type='epi' 时，Number 和 Intro Ep No 可选，但如果填写必须为数字
- Onelink Intro Ep No 始终必填且必须为数字，默认值为 "1"
- Ad Language 和 Onelink Language 始终必填
- Number 和 Intro Ep No 的默认值为空字符串（不是 "false"）
- 使用 Zod schema 定义验证规则
- Onelink Language 默认值与 Ad Language 联动：
  - Ad Language (en) -> Onelink Language (en)
  - Ad Language (kr) -> Onelink Language (ko)
  - Ad Language (jp) -> Onelink Language (ja)
  - Ad Language (id) -> Onelink Language (id)
  - Ad Language (th) -> Onelink Language (en)（Thailand 联动到 English，不是 Chinese）
  - 其他 -> Onelink Language (en)
- React Hook Form 集成
- 支持数组字段验证（多个 Ad）

#### 7. ResultDisplay 组件
**位置**: `frontend/components/output/ResultDisplay.tsx`

**功能**:
- 展示所有生成结果（Campaign Name、Ad Set Name、多个 Ad Name 和对应的 OneLink URL）
- 提供逐条复制按钮

**Props**:
```typescript
interface ResultDisplayProps {
  campaignName: string;
  adSetName: string;
  adResults: Array<{
    adName: string;
    oneLinkUrl: string;
  }>;
}
```

**子组件**:
- ResultCard: 单个结果卡片（包含标签、内容、复制按钮）
- AdResultCard: Ad 结果卡片（包含 Ad Name 和对应的 OneLink URL，成对显示）

### 状态管理

#### 认证状态
- 使用 Context API (`AuthContext`)
- 存储用户信息、Token
- 提供登录/登出方法

#### 应用状态（Program Selection）
- 使用 Context 或 Zustand 管理当前选中的剧目、选中时间、推荐标签
- 暴露 `selectProgram`、`clearProgram` 方法供 ProgramList/ProgramSummary 调用
- 选中剧目后触发表单预填充与步骤高亮切换

#### 表单状态
- 使用 React Hook Form 管理表单状态
- 使用 Zod 进行验证
- 根据选中剧目自动重置表单默认值

#### 服务器状态
- 使用 React Query 管理 API 数据（剧目列表、搜索结果、生成结果）
- 对列表数据启用分页缓存与搜索缓存

### API 客户端设计

**位置**: `frontend/lib/api-client.ts`

**功能**:
- 配置 Axios 实例
- 设置 baseURL（根据环境变量）
- 添加请求拦截器（附加 JWT Token）
- 添加响应拦截器（处理错误）

**示例**:
```typescript
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## 后端设计

### 服务层设计

#### 1. AuthService
**位置**: `backend/app/services/auth_service.py`

**功能**:
- 验证 Firebase Authentication ID Token
- 校验邮箱是否在白名单域名或邮箱列表中
- 生成/维护后端会话 Token（如自定义 JWT 或 Session）
- 提取邮箱前缀

**方法**:
```python
async def login(id_token: str) -> dict:
    """验证 Firebase ID Token 并返回会话信息"""

async def verify_token(token: str) -> dict:
    """验证后端颁发的 Token（如果有）并返回用户信息"""

def extract_email_prefix(email: str) -> str:
    """提取邮箱前缀"""

def is_whitelisted(email: str) -> bool:
    """判断邮箱是否在白名单内"""
```

**实现要点**:
- 使用 Firebase Admin SDK 或 Google 公钥验证 ID Token
- 解析 Token 中的 email 字段
- 白名单来源：配置文件、环境变量或数据库（Cloud SQL/Firestore）
- 非白名单邮箱直接拒绝登录

#### 2. NamingService
**位置**: `backend/app/services/naming_service.py`

**功能**:
- 生成 Campaign Name、Ad Set Name 和 Ad Name 根据 SOP 规则

**方法**:
```python
@staticmethod
def generate_campaign_name(
    country: str,
    media_source: str,
    mkt_type: str,
    target_type: str | None,
    optimization_types: str,
    os: str,
    program_code: str,
    program_shortner: str,  # 如果为空，使用 title 作为兜底
    title: str,  # 用于兜底
    event_type: str | None,
    user_email_prefix: str,
    optional_campaign: str | None,
) -> str:
    """
    生成 Campaign Name
    
    格式: [Country]_[Media source]_[Mkt type]_[Target type]_[Optimization abbreviation]_[Optimization types]_[OS]_[Program code]_[Program shortner/Title]_[Event type]_cn_[User email prefix]_[Optional (Campaign)]
    
    规则:
    - Program shortner: 如果未匹配到，使用 Title 作为兜底（空格转换为下划线，并转换为小写）
    - Program shortner 和 Title 一律转换为小写
    - 'cn' 在 User email prefix 之前添加，表示团队归属
    - 如果未获取到登录用户，user_email_prefix 为空，但 'cn' 仍会保留
    """

@staticmethod
def generate_adset_name(...) -> str:
    """生成 Ad Set Name"""

@staticmethod
def generate_ad_name(
    program_code: str,
    title_en_shortener: str,
    creative_type: str,  # 直接使用原值，不进行缩写
    number: str | None,
    intro_ep_no: str | None,
    text_included: bool,
    concept_keyword: str | None,
    language: str,
    user_email_prefix: str = "",
) -> str:
    """
    生成单个 Ad Name
    
    格式: video_[Program code]_[Title(EN/Shortener)]_[creative type]_[Number]_[Intro Ep No]_[Text included]_[concept keyword_intro]_[Language]_cn_[User email prefix]
    
    规则:
    - Creative Type: 选项为 Highlight、Teaser、Episode，对应命名中分别为 'highlight'、'teaser'、'epi'
    - Number 和 Intro Ep No: 当 creative_type='highlight' 或 'epi' 时必填，否则跳过
    - 'cn' 在 User email prefix 之前添加，表示团队归属（仅一个 'cn'，无固定后缀）
    - 如果未获取到登录用户，user_email_prefix 为空，但 'cn' 仍会保留
    - Title(EN/Shortener) 和 Program Shortener/Title 一律转换为小写
    """

@staticmethod
def generate_ad_names(
    program_code: str,
    title_en_shortener: str,
    ads: List[dict],
    user_email_prefix: str = "",
) -> List[str]:
    """批量生成 Ad Name"""
```

#### 3. OneLinkService
**位置**: `backend/app/services/onelink_service.py`

**功能**:
- 根据 SOP 规则生成 OneLink URL
- 支持批量生成（最多 30 个）
- 处理媒体来源 PID 映射
- 处理 `deep_link_sub1` 重复出现
- 处理 `af_dp` 整体编码

**方法**:
```python
@staticmethod
def generate_onelink_url(
    base_url: str,
    media_source: str,
    campaign_name: str,
    adset_name: str,
    ad_name: str,
    program_id: str,  # 来自 Google Sheets "All" sheet 的 "id" 字段
    season_id: str,   # 来自 Google Sheets "All" sheet 的 "seasonId" 字段
    onelink_intro_ep_no: str,  # Onelink Intro Ep No (required, default "1")
    language: str,
    fixed_params: dict | None = None,
) -> str:
    """生成单个 OneLink URL"""

@staticmethod
def generate_onelink_urls(
    base_url: str,
    media_source: str,
    campaign_name: str,
    adset_name: str,
    ad_names: List[str],
    program_id: str,  # 来自 Google Sheets "All" sheet 的 "id" 字段
    season_id: str,   # 来自 Google Sheets "All" sheet 的 "seasonId" 字段
    ads: List[dict],  # Each dict contains: language, onelinkIntroEpNo
    fixed_params: dict | None = None,
) -> List[str]:
    """批量生成 OneLink URL"""
```

**实现要点**:
- `program_id` 参数必须来自 Google Sheets "All" sheet 的 "id" 字段
- `season_id` 参数来自 Google Sheets "All" sheet 的 "seasonId" 字段（如存在）
- `deep_link_sub1` 使用 `program_id` 的值，并在 URL 中出现两次
- `af_web_dp` 使用格式：`https://www.vigloo.com/{onelink_language}/video/{program_id}?episode={onelink_intro_ep_no}`（使用 Onelink Language 和 Onelink Intro Ep No，Onelink Language 映射规则：en, ko, ja, id, zh）
- `af_dp` 使用格式：`vigloo://deeplink/program?programId={program_id}&seasonId={season_id}&episodeNumber={onelink_intro_ep_no}`，整体进行 URL 编码（使用 Onelink Intro Ep No）
- 所有参数使用标准 URL 编码

#### 4. 数据服务 (Data Service)
- `GoogleSheetsService`：封装 Google Sheets API，读取 Program Info 数据
- `ProgramRepository`：提供获取完整剧目列表、分页、排序、推荐标记、搜索、缓存

#### 5. **API 路由** (API Routes)
- `/api/auth/login` - 用户登录
- `/api/auth/logout` - 用户登出
- `/api/data/programs` - 查询剧目列表（支持分页/搜索/排序）
- `/api/generate/all` - 批量生成所有结果（Campaign Name、Ad Set Name、多个 Ad Name 和对应的 OneLink URL）

### 数据访问层设计

#### 1. ProgramRepository
**位置**: `backend/app/repositories/program_repository.py`

**功能**:
- 封装 Program Info 数据访问
- 实现缓存逻辑
- 支持按上线时间倒序排序、分页、推荐标记、关键字过滤

**方法**:
```python
async def list_programs(
    page: int,
    page_size: int,
    keyword: str | None = None
) -> PaginatedPrograms:
    """返回倒序排序的剧目列表"""

async def get_by_code(program_code: str) -> Optional[ProgramInfo]:
    """根据 Program Code 获取"""

async def refresh_from_sheets() -> None:
    """从 Google Sheets 刷新数据"""
```

#### 2. UserRepository
**位置**: `backend/app/repositories/user_repository.py`

**功能**:
- 用户数据 CRUD

**方法**:
```python
async def get_by_email(email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    
async def create_user(email: str, email_prefix: str) -> User:
    """创建用户"""
```

### 数据模型设计

#### Pydantic Schemas（请求/响应）

**位置**: `backend/app/schemas/`

**generation.py**:
```python
class GenerationRequest(BaseModel):
    program_code: str
    campaign: CampaignFields
    adset: AdSetFields
    ads: AdFields[]  # 数组，最多 30 个

class GenerationResponse(BaseModel):
    campaign_name: str
    ad_set_name: str
    ad_results: List[AdResult]  # 数组，每个包含 ad_name 和 one_link_url
```

**program.py**:
```python
class ProgramInfo(BaseModel):
    program_code: str  # 从 All sheet 的 "ProgramCode" 列获取
    title: str  # 从 En sheet 的 "Title" 列获取（通过 ProgramCode 匹配）
    program_id: str  # 从 All sheet 的 "id" 列获取（用于 OneLink URL 生成中的 programId 参数）
    season_id: str | None  # 从 All sheet 的 "seasonId" 列获取（可选，用于 OneLink URL 生成中的 seasonId 参数）
    program_shortner: str  # 从 Shortener sheet 的 "Title (Shortner)" 列获取（根据 ProgramCode 匹配）；如果未匹配到，在 Campaign Name 生成时使用 title 作为兜底
    title_en_shortener: str  # 从 Shortener sheet 的 "Title (Shortner)" 列获取，如果不存在或为空则使用 En sheet 的 title
    base_one_link_url: str  # 默认值: "https://vigloo.onelink.me/SrIM"
    fixed_params: dict  # JSON 格式的固定参数
```

**字段自动匹配说明**:
- Program Shortener: 根据 Program Code 在 Google Sheets 的 "Shortener" sheet 的 "Title (Shortner)" 字段中自动匹配（注意字段名拼写为 Shortner）
- Title(EN/Shortener): 优先从 "Shortener" sheet 的 "Title (Shortner)" 字段获取，如果不存在或为空，则默认使用 "En" sheet 的 "Title"
- Title(EN/Shortener) 在用于命名生成时，所有空格必须转换为下划线

#### SQLAlchemy Models（数据库）

**位置**: `backend/app/models/`

**user.py**:
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    email_prefix = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**generation_history.py**:
```python
class GenerationHistory(Base):
    __tablename__ = "generation_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    program_code = Column(String)
    campaign_name = Column(String)
    ad_set_name = Column(String)
    # ad_name 和 one_link_url 存储在 payload JSON 中的 ad_results 数组
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**program_cache.py**:
```python
class ProgramCache(Base):
    __tablename__ = "program_cache"
    
    program_code = Column(String, primary_key=True)
    payload = Column(JSON)
    refreshed_at = Column(DateTime)
```

**program_info.py** (新增):
```python
class ProgramInfo(Base):
    __tablename__ = "program_info"
    
    program_code = Column(String, primary_key=True)
    program_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    sub_title = Column(String, default="")
    synopsis = Column(Text, default="")
    episode_count = Column(Integer, nullable=False)
    release_date = Column(Date, nullable=True)
    content_information = Column(String, default="")
    program_shortner = Column(String, default="")
    title_en_shortener = Column(String, nullable=False)
    season_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_program_info_program_id', 'program_id'),
        Index('idx_program_info_release_date', 'release_date'),
    )
```

## 数据库设计

### 表结构

#### users 表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    email_prefix TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);
```

#### generation_history 表
```sql
CREATE TABLE generation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    program_code TEXT,
    campaign_name TEXT,
    ad_set_name TEXT,
    ad_name TEXT,
    one_link_url TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_history_user_id ON generation_history(user_id);
CREATE INDEX idx_history_created_at ON generation_history(created_at DESC);
```

#### program_cache 表
```sql
CREATE TABLE program_cache (
    program_code TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    refreshed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_cache_refreshed_at ON program_cache(refreshed_at);
```

## API 设计详情

### POST /api/auth/login

**请求**:
```json
{
  "idToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ij..."
}
```

**响应**:
```json
{
  "success": true,
  "token": "<backend_session_token>",
  "user": {
    "email": "user@company.com",
    "emailPrefix": "user"
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "error": "Unauthorized"
}
```

**验证逻辑**:
- 校验 ID Token
- 判断邮箱是否在白名单内
- 返回后端会话 Token（如需）

### GET /api/data/programs?q=romantic

**响应**:
```json
{
  "success": true,
  "results": [
    {
      "programCode": "KR000P05S01",
      "title": "Romantic Island",
      "programId": "P05",
      "seasonId": "S01",
      "programShortner": "romantic_island",
      "titleENShortener": "RomanticIsland"
    }
  ]
}
```

### POST /api/generate/all

**请求**:
```json
{
  "programCode": "KR000P05S01",
  "campaign": {
    "country": "us",
    "mediaSource": "fb",
    "mktType": "ua",
    "targetType": "auto",
    "optimizationTypes": "purchase",
    "os": "w2a",
    "eventType": "",
    "optionalCampaign": "han"
  },
  "adset": {
    "optionalAdSet": "test01"
  },
  "ads": [
    {
      "creativeType": "highlight",
      "number": "05",
      "introEpNo": "02",
      "onelinkIntroEpNo": "1",
      "textIncluded": true,
      "conceptKeyword": "kiss",
      "adLanguage": "en",
      "onelinkLanguage": "en"
    },
    {
      "creativeType": "epi",
      "textIncluded": true,
      "onelinkIntroEpNo": "1",
      "adLanguage": "kr",
      "onelinkLanguage": "ko"
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "campaignName": "us_fb_ua_auto_e_purchase_w2a_KR000P05S01_romantic_island_user_han",
    "adSetName": "us_fb_ua_auto_e_purchase_w2a_KR000P05S01_romantic_island_user_han_test01",
    "adResults": [
      {
        "adName": "video_KR000P05S01_Romantic Island_RomanticIsland_hight_05_02_txt_kiss_intro_en_cn",
        "oneLinkUrl": "http://onelink.com/base?pid=P05&s=S01&c=us_fb_ua_auto_e_purchase_w2a_KR000P05S01_romantic_island_user_han&af_adset=us_fb_ua_auto_e_purchase_w2a_KR000P05S01_romantic_island_user_han_test01&af_ad=video_KR000P05S01_Romantic Island_RomanticIsland_hight_05_02_txt_kiss_intro_en_cn"
      },
      {
        "adName": "video_KR000P05S01_Romantic Island_RomanticIsland_epi_txt_en_cn",
        "oneLinkUrl": "http://onelink.com/base?pid=P05&s=S01&c=us_fb_ua_auto_e_purchase_w2a_KR000P05S01_romantic_island_user_han&af_adset=us_fb_ua_auto_e_purchase_w2a_KR000P05S01_romantic_island_user_han_test01&af_ad=video_KR000P05S01_Romantic Island_RomanticIsland_epi_txt_en_cn"
      }
    ]
  }
}
```

### GET /api/data/programs
```typescript
Request:
  Query Parameters:
    page?: number (default 1)
    pageSize?: number (default 20)
    keyword?: string  // Program Code 或 Title 关键字

Response:
{
  "success": boolean;
  "pagination": {
    "current": number;
    "pageSize": number;
    "total": number;
  };
  "results": Array<{
    programCode: string;
    title: string;
    programShortner: string;
    programId: string;
    seasonId: string;
    releasedAt: string;
    status?: string;
    isRecommended?: boolean;
  }>;
}
```

### GET /api/data/programs/:code
- 保留按 Code 查询单个剧目信息的能力（可选）

## UI/UX 设计

### 设计原则
- 简洁明了，减少认知负担
- 明确呈现“三步流程”：选择剧目 → 配置策略 → 复制结果
- 列表、搜索、表单、结果模块布局一致，支持桌面与移动端
- 实时验证反馈
- 生成结果突出显示

### 布局设计

#### 桌面端布局
```
┌───────────────────────────────────────────────┐
│  Header (Logo, Step Indicator, User Info)     │
├───────────────────────────────────────────────┤
│  Step Tabs/Indicator: [1 选择剧目] [2 填写策略] [3 复制结果]
├───────────────────────────────────────────────┤
│  ┌───────────── 左侧/上部 (步骤 1) ───────────┐ ┌───────────┐
│  │ ProgramSearch + ProgramList (倒序 + 推荐) │ │ 右侧/下部 │
│  │ - 列表行含 “去创建广告”                  │ │ (步骤 2&3) │
│  │ - 支持推荐标签、高亮                     │ │           │
│  └───────────────────────────────────────────┘ │  ┌───────┐ │
│                                                  │  │步骤2 │ │
│                                                  │  │表单  │ │
│                                                  │  └───────┘ │
│                                                  │  ┌───────┐ │
│                                                  │  │步骤3 │ │
│                                                  │  │结果  │ │
│                                                  │  └───────┘ │
│                                                  └───────────┘
└───────────────────────────────────────────────┘
```

#### 移动端布局
- 顶部 Stepper 指示当前步骤
- 步骤 1 列表占据首屏，列表项卡片化；点击后折叠并展开步骤 2 表单
- 步骤 3 结果通过折叠面板或全屏浮层展示，复制按钮固定在底部

### 交互设计

#### 步骤切换
1. 默认进入步骤 1，加载倒序剧目列表
2. 搜索关键词时，列表实时过滤并自动高亮匹配文本
3. 点击“去创建广告”后：
   - 保存当前选中剧目
   - Stepper 高亮步骤 2
   - 自动滚动到策略表单区域

#### 策略配置
1. 表单顶部显示当前剧目摘要（Program Code、上线时间、推荐标签等）
2. 支持返回步骤 1 重新选择剧目
3. 表单验证失败时保持在步骤 2，并提示错误

#### 生成与复制
1. 点击“生成”按钮触发步骤 3，展示全部输出
2. 每个结果提供复制按钮与成功提示
3. 支持“返回步骤 2”重新调整策略或“选择其他剧目”回到步骤 1

## 错误处理设计

### 前端错误处理
- API 错误统一处理（Axios 拦截器）
- 显示用户友好的错误消息
- 网络错误重试机制
- 表单验证错误实时反馈

### 后端错误处理
- 统一错误响应格式
- HTTP 状态码正确使用
- 错误日志记录（Cloud Logging）
- 异常捕获和优雅降级

### 错误场景

#### Google Sheets API 失败
- 回退到缓存数据
- 显示警告提示
- 记录错误日志

#### 数据库连接失败
- 返回 503 状态码
- 显示服务不可用提示
- 触发告警

## 安全设计

### 认证安全
- 使用 Firebase Authentication（Google Sign-In）
- 后端必须验证 ID Token 签名与过期时间
- 校验邮箱是否在白名单中（域名或具体邮箱）
- 对非法或未授权用户返回 401/403

### 数据安全
- 所有 API 使用 HTTPS
- 敏感信息加密存储
- 服务账号凭证存储在 Secret Manager
- 实现 API 速率限制

### 输入验证
- 前端和后端双重验证
- SQL 注入防护（使用参数化查询）
- XSS 防护（输入转义）

## 性能优化设计

### 前端优化
- Next.js 自动代码分割
- 图片优化（如有）
- React Query 缓存
- 防抖搜索输入

### 后端优化
- FastAPI 异步处理
- 数据缓存机制
- 数据库连接池
- Cloud Run 自动扩缩容

### 缓存策略
- Program Info 缓存 TTL: 5 分钟
- 搜索结果缓存：最近 10 次查询
- 生成结果不缓存（每次重新生成）

## 部署设计

### 前端部署
- 构建：`npm run build`
- 部署到 Firebase Hosting
- 配置自定义域名
- 启用 HTTPS

### 后端部署
- 构建 Docker 镜像
- 推送到 Artifact Registry
- 部署到 Cloud Run
- 配置环境变量
- 配置健康检查

### CI/CD 流程
1. 代码推送到 GitHub
2. GitHub Actions 触发
3. 运行测试
4. 构建 Docker 镜像
5. 推送到 Artifact Registry
6. 部署到 Cloud Run
7. 前端构建并部署到 Firebase Hosting

## 监控和日志

### 监控指标
- API 响应时间
- 错误率
- 请求量
- 缓存命中率

### 日志记录
- API 请求日志
- 错误日志
- 业务操作日志（生成记录）

### 告警
- API 错误率 > 5%
- 响应时间 > 2s
- 服务不可用

## 测试设计

### 单元测试
- 命名规则函数测试
- 工具函数测试
- 组件测试

### 集成测试
- API 端点测试
- 数据库操作测试
- Google Sheets API 测试（Mock）

### 端到端测试
- 完整生成流程测试
- 用户登录流程测试
- 错误场景测试

## Program Info 数据库同步设计

### 数据库表设计

#### program_info 表
```sql
CREATE TABLE program_info (
    program_code VARCHAR(50) PRIMARY KEY,
    program_id VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    sub_title VARCHAR(500) DEFAULT '',
    synopsis TEXT DEFAULT '',
    episode_count INTEGER NOT NULL,
    release_date DATE,
    content_information VARCHAR(200) DEFAULT '',
    program_shortner VARCHAR(200) DEFAULT '',
    title_en_shortener VARCHAR(500) NOT NULL,
    season_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_program_info_program_id ON program_info(program_id);
CREATE INDEX idx_program_info_release_date ON program_info(release_date);
CREATE INDEX idx_program_info_updated_at ON program_info(updated_at);
```

### 同步服务设计

#### 服务层：ProgramSyncService

**位置**: `backend/app/services/program_sync_service.py`

**职责**:
- 从 Google Sheets 读取 Program Info 数据
- 与数据库中的数据进行对比
- 执行增量更新（只更新有变化的记录）
- 记录同步日志

**核心方法**:
```python
class ProgramSyncService:
    async def sync_from_sheets(self, db: AsyncSession) -> SyncResult:
        """
        从 Google Sheets 同步数据到数据库
        
        Returns:
            SyncResult: 包含同步统计信息（新增、更新、删除数量）
        """
    
    async def _detect_changes(
        self, 
        sheets_data: List[ProgramInfo], 
        db_data: List[ProgramInfo]
    ) -> ChangeSet:
        """
        检测数据变化
        
        Returns:
            ChangeSet: 包含新增、更新、删除的记录列表
        """
```

#### 定时任务设计

**使用 APScheduler** (已在技术栈中)

**配置**:
- 时区: `Asia/Shanghai` (UTC+8)
- 执行时间: 每天 09:00, 12:00, 18:00 (北京时间)
- 任务类型: `cron` job

**实现位置**: `backend/app/core/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))

@scheduler.scheduled_job(
    CronTrigger(hour=9, minute=0, timezone='Asia/Shanghai'),
    id='sync_program_info_morning'
)
@scheduler.scheduled_job(
    CronTrigger(hour=12, minute=0, timezone='Asia/Shanghai'),
    id='sync_program_info_noon'
)
@scheduler.scheduled_job(
    CronTrigger(hour=18, minute=0, timezone='Asia/Shanghai'),
    id='sync_program_info_evening'
)
async def sync_program_info():
    """定时同步 Program Info 数据"""
    # 实现同步逻辑
```

#### API 端点设计

**手动触发同步**:
```http
POST /api/admin/sync/programs
Response: {
    "success": true,
    "result": {
        "created": 10,
        "updated": 5,
        "deleted": 2,
        "total": 359
    }
}
```

### 数据访问层重构

#### ProgramRepository 重构

**变更**:
- `get_all_programs()`: 从数据库读取，不再从 Google Sheets 读取
- `search_programs()`: 从数据库查询，使用 SQL LIKE 查询
- 移除缓存逻辑（数据库本身就是缓存）

**新的实现**:
```python
class ProgramRepository:
    async def get_all_programs(self) -> List[ProgramInfo]:
        """从数据库读取所有 Program Info"""
        stmt = select(ProgramInfo).order_by(ProgramInfo.release_date.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search_programs(self, query: str) -> List[ProgramInfo]:
        """从数据库搜索 Program Info"""
        query_lower = query.lower().strip()
        stmt = select(ProgramInfo).where(
            or_(
                ProgramInfo.program_code.ilike(f"%{query_lower}%"),
                ProgramInfo.title.ilike(f"%{query_lower}%")
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

### 错误处理

- Google Sheets API 失败: 记录错误日志，但不影响数据库读取
- 数据库连接失败: 记录错误，定时任务重试
- 数据格式错误: 跳过错误记录，记录警告日志

## 变更历史

| 日期 | 版本 | 变更说明 | 变更人 |
|------|------|----------|--------|
| 2025-01-11 | 1.0 | 初始版本 | AI Assistant |
| 2025-01-11 | 1.1 | 添加 Program Info 数据库同步设计 | AI Assistant |

