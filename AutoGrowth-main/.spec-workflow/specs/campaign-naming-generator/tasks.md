# 任务文档

## 项目信息

**规范名称**: campaign-naming-generator

**项目名称**: 短剧投放命名与链接自动化生成器

**创建日期**: 2025-01-11

**状态**: 待审批

**依赖文档**: requirements.md, design.md

## 任务列表

### 阶段 1: 项目初始化与基础设施

#### Task 1.1: 初始化前端项目结构
- [x] **状态**: 已完成
- **文件**: 
  - `frontend/package.json`
  - `frontend/next.config.mjs`
  - `frontend/tsconfig.json`
  - `frontend/tailwind.config.js`
  - `frontend/.env.example`
- **需求**: NFR-004 (兼容性需求)
- **描述**: 创建 Next.js 14 项目，配置 TypeScript、Tailwind CSS、Ant Design

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Infrastructure Developer

**Task**: 
初始化 Next.js 14 前端项目，配置所有必要的依赖和构建工具。创建项目基础结构，包括配置文件、环境变量示例、TypeScript 配置、Tailwind CSS 配置。

**Restrictions**:
- 不要创建业务组件或页面
- 不要配置 API 路由（除非是 Next.js 必需的）
- 确保使用 Next.js 14 App Router 模式
- 不要添加不必要的依赖

**_Leverage**:
- 参考 `.spec-workflow/steering/structure.md` 中的前端目录结构
- 参考 `.spec-workflow/steering/tech.md` 中的技术栈选择

**_Requirements**:
- NFR-004: 兼容性需求（支持主流浏览器）

**Success**:
- `npm install` 成功执行
- `npm run dev` 可以启动开发服务器
- TypeScript 编译无错误
- Tailwind CSS 正常工作
- 项目结构符合 design.md 中的定义

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 1.2: 初始化后端项目结构
- [x] **状态**: 已完成
- **文件**:
  - `backend/requirements.txt`
  - `backend/pyproject.toml` (可选)
  - `backend/Dockerfile`
  - `backend/.env.example`
  - `backend/app/main.py`
  - `backend/app/core/config.py`
- **需求**: NFR-003 (安全需求)
- **描述**: 创建 FastAPI 项目，配置依赖、Docker、环境变量管理

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Infrastructure Developer

**Task**:
初始化 FastAPI 后端项目，配置 Python 依赖、Docker 容器、环境变量管理。创建基础的项目结构和配置文件。

**Restrictions**:
- 不要实现业务逻辑
- 不要创建数据库模型（下一阶段）
- 确保使用 Python 3.11
- 不要添加不必要的依赖

**_Leverage**:
- 参考 `.spec-workflow/steering/structure.md` 中的后端目录结构
- 参考 `.spec-workflow/steering/tech.md` 中的技术栈选择

**_Requirements**:
- NFR-003: 安全需求（环境变量管理）

**Success**:
- `pip install -r requirements.txt` 成功
- Docker 镜像可以构建
- FastAPI 应用可以启动（即使只有基础路由）
- 环境变量从 `.env` 文件正确加载

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 1.3: 配置数据库和迁移
- [x] **状态**: 已完成
- **文件**:
  - `backend/app/models/__init__.py`
  - `backend/app/models/user.py`
  - `backend/app/models/generation_history.py`
  - `backend/app/models/program_cache.py`
  - `backend/app/core/database.py`
  - `backend/alembic.ini` (可选)
  - `backend/alembic/env.py` (可选)
- **需求**: DR-002 (用户数据存储)
- **描述**: 创建 SQLAlchemy 模型，配置数据库连接，创建迁移脚本

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Database Developer

**Task**:
创建数据库模型和连接配置。实现 users、generation_history、program_cache 三个表的 SQLAlchemy 模型，配置 Cloud SQL PostgreSQL 连接，创建数据库迁移脚本。

**Restrictions**:
- 不要实现业务逻辑服务
- 确保模型字段与 design.md 中的定义一致
- 不要硬编码数据库连接信息（使用环境变量）

**_Leverage**:
- 参考 `design.md` 中的数据库设计部分
- 参考 `requirements.md` 中的 DR-002 数据需求

**_Requirements**:
- DR-002: 用户数据存储需求

**Success**:
- 所有模型类正确定义
- 数据库连接配置正确
- 迁移脚本可以创建表结构
- 模型关系（外键）正确定义

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 2: 认证与用户管理

#### Task 2.1: 实现后端认证服务
- [ ] **状态**: 待开始
- **文件**:
  - `backend/app/services/auth_service.py`
  - `backend/app/core/security.py`
  - `backend/app/api/v1/auth.py`
  - `backend/app/schemas/auth.py`
  - `backend/app/utils/whitelist.py`
- **需求**: US-001 (用户登录与身份识别)
- **描述**: 实现基于 Firebase Authentication 的后端认证服务，验证 Google ID Token、校验白名单、生成/管理后端会话

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Authentication Developer

**Task**:
- 接收前端传递的 Firebase ID Token
- 使用 Firebase Admin SDK（或 Google 公钥）验证 ID Token 的合法性、签名与过期时间
- 校验用户邮箱是否位于白名单域名/邮箱列表中（引用配置或数据库）
- 提取邮箱前缀，创建后端会话（如颁发 JWT 或 Session Cookie）
- 提供登录、登出、Token 刷新接口

**Restrictions**:
- 不要实现前端界面
- 不要硬编码白名单（从配置或数据库读取）
- 对未授权或白名单外的用户返回 401/403
- 确保所有敏感配置从环境变量/Secret Manager 加载

**_Leverage**:
- 参考 `design.md` 中更新后的 AuthService 设计
- 参考 `requirements.md` 中 US-001 的验收标准

**_Requirements**:
- US-001: 用户登录与身份识别

**Success**:
- `/api/auth/login` 接口可接受 ID Token 并完成校验
- 白名单机制生效（非授权邮箱被拒绝）
- 成功登录返回用户信息（邮箱、邮箱前缀）和后端会话 Token（如需）
- `/api/auth/logout`、`/api/auth/refresh`（如实现）工作正常
- 单元测试覆盖合法 Token、非法 Token、非白名单邮箱等场景

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 2.2: 实现前端认证功能
- [ ] **状态**: 待开始
- **文件**:
  - `frontend/app/login/page.tsx`
  - `frontend/components/auth/LoginForm.tsx`
  - `frontend/context/AuthContext.tsx`
  - `frontend/hooks/useAuth.ts`
  - `frontend/lib/auth.ts`
  - `frontend/lib/api-client.ts`
- **需求**: US-001 (用户登录与身份识别)
- **描述**: 实现 Google Sign-In 登录流程，管理认证状态、处理白名单提示

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Authentication Developer

**Task**:
- 集成 Firebase Authentication（Google Provider）
- 实现 “使用 Google 登录” 按钮并处理成功/失败回调
- 登录成功后获取 ID Token，调用后端 `/api/auth/login`
- 将后端会话 Token/状态保存到 Context，支持持久化
- 为非白名单用户显示无权限提示
- 未登录用户访问受保护页面时跳转到登录页

**Restrictions**:
- 不要实现业务页面
- 不要在前端维护白名单列表（由后端返回）
- 确保 Token 不暴露在不安全的存储中（优先使用 HttpOnly Cookie）

**_Leverage**:
- 参考 `design.md` 中的前端认证模块设计
- 参考 `requirements.md` 中 US-001 的验收标准

**_Requirements**:
- US-001: 用户登录与身份识别

**Success**:
- 登录页面显示 Google Sign-In 按钮
- 合法用户可成功登录并跳转到主页面
- 非白名单用户收到明确提示并无法访问主页面
- 登录状态在页面刷新后仍保持
- 登出操作清理所有认证状态

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 3: 数据访问层

#### Task 3.1: 实现 Google Sheets 集成
- [x] **状态**: 已完成
- **文件**:
  - `backend/app/services/google_sheets_service.py`
  - `backend/app/repositories/program_repository.py`
  - `backend/app/core/google_sheets.py`
- **需求**: US-002 (剧目列表浏览), US-003 (剧目信息搜索), INT-001 (Google Sheets API 集成)
- **描述**: 实现 Google Sheets API 调用，拉取 Program Info 数据，为剧目列表与搜索提供数据源，并实现缓存机制

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Data Integration Developer

**Task**:
实现 Google Sheets API 集成，包括服务账号认证、Program Info 表数据读取、排序字段、推荐标记等扩展字段加载，以及缓存机制（写入 Cloud SQL program_cache 表）。确保既能支持完整列表，也能支持搜索过滤。

**Restrictions**:
- 不要实现前端列表或搜索界面（后续任务完成）
- 缓存 TTL 设置为 5 分钟
- 确保服务账号凭证从 Secret Manager 或环境变量读取
- 不要硬编码 Sheet ID（使用环境变量）

**_Leverage**:
- 参考 `design.md` 中的 GoogleSheetsService 设计
- 参考 `requirements.md` 中的 US-002、US-003 和 INT-001

**_Requirements**:
- US-002: 剧目列表浏览与快速进入
- US-003: 剧目信息搜索与自动完成
- INT-001: Google Sheets API 集成

**Success**:
- 可以成功连接 Google Sheets API
- 可以读取 Program Info 表数据并包含排序所需字段（上线时间等）
- 搜索功能正常工作（支持 Program Code 和 Title）
- 缓存机制正常工作（写入和读取）
- API 限流时正确回退到缓存

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 3.2: 实现剧目列表 API
- [x] **状态**: 已完成
- **文件**:
  - `backend/app/api/v1/programs.py`
  - `backend/app/schemas/program.py`
- **需求**: US-002 (剧目列表浏览), INT-006 (剧目列表 API 集成)
- **描述**: 创建获取剧目列表的 API，支持按上线时间倒序、分页、推荐标记等信息

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend API Developer

**Task**:
实现 `/api/data/programs` 端点，返回倒序排序的剧目列表，支持分页、筛选、推荐标记，并与搜索参数联动（keyword）。响应需包含列表展示所需的全部字段。

**Restrictions**:
- 不要实现前端组件
- 确保响应时间 < 500ms（使用缓存）
- 支持 `keyword` 参数进行模糊查询
- 返回值需包含分页信息（total、page、pageSize）

**_Leverage**:
- 参考 `design.md` 中的 API 设计
- 使用 Task 3.1 实现的数据服务

**_Requirements**:
- US-002: 剧目列表浏览与快速进入
- INT-006: 剧目列表 API 集成

**Success**:
- API 端点正常工作
- 默认按上线时间倒序返回
- 支持分页、搜索、推荐标记等字段
- 响应结构符合设计规范

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 3.3: 实现剧目搜索联动
- [x] **状态**: 已完成
- **文件**:
  - `frontend/components/forms/ProgramSearch.tsx`
  - `frontend/hooks/useProgramSearch.ts`
  - `frontend/lib/api-client.ts` (更新)
- **需求**: US-003 (剧目信息搜索), INT-006 (剧目列表 API 集成)
- **描述**: 实现搜索输入框、自动完成下拉列表、防抖搜索，并与列表联动高亮

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Component Developer

**Task**:
实现剧目搜索组件，包括搜索输入框、自动完成下拉列表、防抖搜索（300ms）、选择后触发列表滚动到对应剧目。使用 React Query 管理 API 调用和缓存。

**Restrictions**:
- 不要实现列表组件（下一任务）
- 确保防抖正常工作
- 使用 Ant Design 的 AutoComplete / Input 组件
- 不要硬编码 API URL

**_Leverage**:
- 参考 `design.md` 中的 ProgramSearch 组件设计
- 使用 Task 3.2 实现的 API 端点

**_Requirements**:
- US-003: 剧目信息搜索与自动完成
- INT-006: 剧目列表 API 集成

**Success**:
- 搜索输入框正常工作
- 自动完成下拉列表显示匹配结果
- 防抖功能正常工作
- 选择剧目后列表滚动或高亮对应项
- 加载状态正确显示

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 3.4: 实现剧目列表组件
- [x] **状态**: 已完成
- **文件**:
  - `frontend/components/programs/ProgramList.tsx`
  - `frontend/components/programs/ProgramCard.tsx` (可选)
  - `frontend/hooks/useProgramList.ts`
- **需求**: US-002 (剧目列表浏览), INT-006 (剧目列表 API 集成)
- **描述**: 实现默认展示的剧目列表 UI，支持排序、高亮、行动按钮“去创建广告”

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Feature Developer

**Task**:
实现剧目列表组件，展示按上线时间倒序的剧目，支持分页/无限滚动、推荐标记展示、搜索结果高亮。每条记录提供“去创建广告”按钮，触发 program selection 并跳转到策略表单。

**Restrictions**:
- 确保移动端可用（卡片布局或响应式表格）
- 列表需要显示必要字段（名称、Code、shortner、上线时间、状态等）
- 与搜索组件共享数据源（React Query cache）
- 不要在此任务中实现表单逻辑

**_Leverage**:
- 参考 `design.md` 中的 ProgramList 组件设计
- 使用 Task 3.2 的列表 API 与 Task 3.3 的搜索状态

**_Requirements**:
- US-002: 剧目列表浏览与快速进入
- INT-006: 剧目列表 API 集成

**Success**:
- 列表加载并显示倒序数据
- 支持分页或无限滚动
- 搜索高亮与选中态正常工作
- “去创建广告”按钮触发 program selection 回调
- 列表在桌面和移动设备上展示良好

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 4: 表单实现

#### Task 4.1: 实现统一策略配置表单组件
- [x] **状态**: 已完成
- **文件**:
  - `frontend/components/forms/StrategyForm.tsx`
  - `frontend/components/forms/AdFormItem.tsx` (Ad 表单项子组件)
  - `frontend/lib/constants.ts` (下拉选项)
  - `frontend/types/form.ts`
- **需求**: US-004 (统一策略配置表单输入), US-012 (表单验证)
- **描述**: 在一个页面实现 Campaign、Ad Set、Ad 的统一表单，支持动态添加多个 Ad（最多 30 个）

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Form Developer

**Task**:
实现统一策略配置表单组件（StrategyForm），在一个页面中包含：
1. Campaign 区域：所有 Campaign 级别字段（Country、Media source、Mkt type 等）、Logged In User 只读显示
2. Ad Set 区域：Optional (Ad Set) 必填字段
3. Ad 列表区域：支持动态添加多个 Ad 表单（最多 30 个），每个 Ad 包含所有字段，支持条件字段显示/隐藏逻辑

**Restrictions**:
- 不要实现生成逻辑（后续任务）
- 确保所有下拉选项从 constants.ts 读取
- 使用 Ant Design 表单组件和 React Hook Form
- 使用 Zod 进行验证
- 验证错误实时显示
- 至少保留一个 Ad，最多 30 个 Ad
- 每个 Ad 支持删除（至少保留一个）

**_Leverage**:
- 参考 `design.md` 中的 StrategyForm 组件设计
- 参考 `requirements.md` 中的 US-004 和 US-012

**_Requirements**:
- US-004: 统一策略配置表单输入
- US-012: 表单验证与错误提示

**Success**:
- Campaign 区域所有字段正确显示
- Ad Set 区域字段正确显示
- Ad 列表区域初始显示一个 Ad
- "增加 Ad" 按钮正常工作（最多 30 个）
- 每个 Ad 的删除按钮正常工作（至少保留一个）
- 条件字段显示/隐藏逻辑正确（creative type='hight' 时显示 Number 和 Intro Ep No）
- 所有表单验证正常工作
- 错误提示实时显示
- Logged In User 正确显示

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 5: 命名规则引擎

#### Task 5.1: 实现后端命名服务
- [x] **状态**: 已完成
- **文件**:
  - `backend/app/services/naming_service.py`
  - `backend/app/utils/mappings.py` (Optimization abbreviation 映射)
- **需求**: US-007 (Campaign Name 生成), US-008 (Ad Set Name 生成), US-009 (Ad Name 批量生成)
- **描述**: 实现 SOP 命名规则引擎，生成 Campaign Name、Ad Set Name 和多个 Ad Name

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Business Logic Developer

**Task**:
实现命名规则服务，包括：
1. Campaign Name 生成逻辑（1 个）
2. Ad Set Name 生成逻辑（1 个）
3. Ad Name 批量生成逻辑（为每个 Ad 生成一个独立的 Ad Name，最多 30 个）

确保严格按照 SOP 规则，智能跳过空字段，正确处理邮箱前缀附加。Ad Name 生成方法应支持接收 Ad 字段数组并返回对应的 Ad Name 数组。

**Restrictions**:
- 不要修改 SOP 规则（严格按照 requirements.md 定义）
- 确保所有字段顺序正确
- 不要硬编码映射关系（使用配置文件）
- Ad Name 生成方法应支持批量处理

**_Leverage**:
- 参考 `design.md` 中的 NamingService 设计
- 参考 `requirements.md` 中的 US-007、US-008、US-009

**_Requirements**:
- US-007: Campaign Name 自动生成
- US-008: Ad Set Name 自动生成
- US-009: Ad Name 批量自动生成

**Success**:
- Campaign Name 生成符合 SOP 规则（1 个）
- Ad Set Name 生成正确（1 个）
- Ad Name 批量生成正确（数量与输入 Ad 数量一致，最多 30 个，智能跳过空字段）
- 邮箱前缀正确附加
- 所有测试用例通过

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 5.2: 实现 OneLink 批量生成服务
- [x] **状态**: 已完成
- **文件**:
  - `backend/app/services/onelink_service.py`
  - `backend/app/utils/mappings.py`
- **需求**: US-010 (OneLink URL 批量生成)
- **描述**: 实现 OneLink URL 批量生成逻辑，为每个 Ad 生成对应的 OneLink URL，解析媒体来源 PID 映射，处理重复的 `deep_link_sub1`、`af_dp` 整体编码等 SOP 细节

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Business Logic Developer

**Task**:
实现 OneLink 批量生成服务，包括：
- 使用媒体来源到 pid 的映射表（fb → metaweb_int、tt → tiktok_int、go → google_int 等）
- 固定基础 URL `https://vigloo.onelink.me/SrIM`（支持 Program Info 覆盖）
- 为每个 Ad 生成一个独立的 OneLink URL（最多 30 个）
- 每个 OneLink URL 包含：
  - 共享参数：`pid`、`c`（Campaign Name）、`af_adset`（Ad Set Name）、`programId`（来自 Google Sheets "All" sheet 的 "id" 字段）、`seasonId`（来自 Google Sheets "All" sheet 的 "seasonId" 字段）、`deep_link_sub1`（两次，值同 programId，来自 "All" sheet 的 "id" 字段）、`deep_link_sub2`（值同 seasonId）、固定参数等
  - Ad 特定参数：`af_ad`（对应 Ad 的 Ad Name）、`deep_link_sub3`（对应 Ad 的 Episode Number）、`af_web_dp`（使用对应 Ad 的 Language 和 Episode Number，其中 programId 来自 "All" sheet 的 "id" 字段）、`af_dp`（使用对应 Ad 的 Episode Number，其中 programId 和 seasonId 分别来自 "All" sheet 的 "id" 和 "seasonId" 字段）
- `deep_link_sub1` 追加两次、`af_web_dp` 使用对应 Ad 的语言和剧集编号生成、`af_dp` 以整体编码字符串形式拼接
- 保留 fixedParams 中的额外键值对
- OneLink URL 生成方法应支持接收 Ad 数组并返回对应的 OneLink URL 数组

**Restrictions**:
- 不要修改命名服务或生成 API（其他任务负责）
- 不要硬编码媒体来源映射（使用配置/工具模块）
- 确保所有参数使用标准 URL 编码
- OneLink URL 生成方法应支持批量处理

**_Leverage**:
- 参考 `design.md` 中更新后的 OneLinkService 部分
- 参考 `requirements.md` 中 US-010 的验收标准
- 使用 Program Info 数据模型中的字段（programId 来自 "All" sheet 的 "id" 字段，seasonId 来自 "All" sheet 的 "seasonId" 字段）

**_Requirements**:
- US-010: OneLink URL 批量自动生成

**Success**:
- 能够根据媒体来源正确映射 pid
- 生成的 URL 数组数量与 Ad 数量完全一致（最多 30 个）
- 每个 URL 包含所有必需参数：`pid`、`c`、`af_adset`、`af_ad`（对应 Ad）、`programId`、`seasonId`、`deep_link_sub1`（两次）、`deep_link_sub2`、`deep_link_sub3`（对应 Ad）、`af_web_dp`（对应 Ad）、`af_force_deeplink`、`is_retargeting`、`af_dp`（对应 Ad）、`af_reengagement_window`、`af_inactivity_window`、`af_click_lookback`、`deep_link_value`
- `af_dp` 为整体编码后的字符串，`af_web_dp` 使用对应 Ad 的 `language` 与 `episodeNumber`
- 支持 fixedParams 扩展参数
- 单元测试覆盖关键路径并全部通过

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 5.3: 实现批量生成 API 端点
- [x] **状态**: 已完成
- **文件**:
  - `backend/app/api/v1/generate.py`
  - `backend/app/schemas/generation.py`
- **需求**: US-007, US-008, US-009, US-010 (所有生成需求)
- **描述**: 创建 `/api/generate/all` API 端点，整合命名服务与 OneLink 服务，返回完整的批量生成结果（包含 Campaign Name、Ad Set Name、多个 Ad Name 和对应的 OneLink URL）

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend API Developer

**Task**:
实现批量生成 API 端点，接收生成请求（包含 Campaign、Ad Set 字段和 Ad 数组，最多 30 个），调用命名服务和 OneLink 服务，返回包含：
- 1 个 Campaign Name
- 1 个 Ad Set Name
- 多个 Ad Name（数量与请求中 Ad 数量一致）
- 多个 OneLink URL（数量与 Ad Name 数量一致，每个对应一个 Ad）

确保请求中包含每个 Ad 的 episode number（例如 Intro Ep No）和 language，用于 OneLink 参数构建。

**Restrictions**:
- 不要重复实现业务逻辑（应调用 Task 5.1 和 Task 5.2 的服务）
- 确保请求体验证每个 Ad 的语言和 Episode Number 字段
- 响应结构必须包含 Ad 结果数组（每个包含 adName 和 oneLinkUrl）
- 验证 Ad 数量不超过 30 个

**_Leverage**:
- 参考 `design.md` 中的 API 设计
- 使用 Task 5.1 和 Task 5.2 实现的服务

**_Requirements**:
- US-007: Campaign Name 自动生成
- US-008: Ad Set Name 自动生成
- US-009: Ad Name 批量自动生成
- US-010: OneLink URL 批量自动生成

**Success**:
- API 端点正常工作，能够返回批量生成结果
- 请求验证（包括每个 Ad 的 language 与 episode number）正确
- 响应格式符合定义，包含 1 个 Campaign Name、1 个 Ad Set Name、多个 Ad Name 和对应的 OneLink URL
- OneLink URL 数量与 Ad Name 数量完全一致
- 错误处理完善，异常情况返回明确错误信息

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 6: 前端生成功能

#### Task 6.1: 实现页面布局与三步流程
- [x] **状态**: 已完成
- **文件**:
  - `frontend/app/page.tsx`
  - `frontend/components/layout/Header.tsx`
  - `frontend/components/programs/ProgramList.tsx`
  - `frontend/components/forms/*`
- **需求**: US-002 (剧目列表浏览), US-004~US-006 (表单输入), US-010 (结果展示), NFR-004 (兼容性需求)
- **描述**: 构建“选择剧目 → 填写策略 → 复制结果”三步式页面布局，整合列表、搜索、表单与结果区域并提供清晰的导航

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Layout Developer

**Task**:
- 在页面左侧/顶部展示剧目列表和搜索区域，右侧/下方展示策略表单与生成结果
- 维持显式的三步流程指示（Stepper 或标题区域）
- 支持在选定剧目后滚动/聚焦到表单区域，并展示当前剧目信息概览
- 预留返回列表或重新选择剧目的交互
- 确保移动端下三步流程仍清晰可见（折叠或轮播形式）

**Restrictions**:
- 不要在此任务中实现生成按钮逻辑（下一任务）
- 不要实现结果数据处理（下一任务）
- 确保响应式设计（桌面与移动端）

**_Leverage**:
- 参考 `design.md` 中更新的 UI/UX 三步流程
- 使用已实现的 ProgramList、ProgramSearch、表单组件

**_Requirements**:
- US-002: 剧目列表浏览与快速进入
- US-004: 广告系列级别表单输入
- US-005: 广告组级别表单输入
- US-006: 广告级别表单输入
- US-010: 生成结果展示与复制
- NFR-004: 兼容性需求

**Success**:
- 页面清晰呈现“选择剧目 → 填写策略 → 复制结果”的流程
- 列表、搜索、表单、结果模块布局合理且响应式
- 选定剧目后自动展示概览信息并滚动/聚焦到表单
- 导航栏正确显示用户信息与登出入口

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 6.2: 实现批量生成逻辑和结果展示
- [x] **状态**: 已完成
- **文件**:
  - `frontend/hooks/useGeneration.ts`
  - `frontend/components/output/ResultDisplay.tsx`
  - `frontend/components/output/ResultCard.tsx`
  - `frontend/components/output/AdResultCard.tsx`
  - `frontend/lib/clipboard.ts`
- **需求**: US-011 (生成结果展示与复制)
- **描述**: 实现批量生成 API 调用、结果展示组件（支持多个 Ad 结果）、逐条复制到剪贴板功能

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Frontend Feature Developer

**Task**:
实现批量生成功能，包括：
1. 调用批量生成 API（传递 Campaign、Ad Set 字段和 Ad 数组）
2. 显示生成结果：
   - 1 个 Campaign Name（独立卡片）
   - 1 个 Ad Set Name（独立卡片）
   - 多个 Ad 结果卡片（每个包含 Ad Name 和对应的 OneLink URL，成对显示）
3. 每个结果都有独立的复制按钮，支持逐条复制
4. 视觉反馈（Toast 提示）
5. 使用 React Query 管理 API 调用状态

**Restrictions**:
- 不要修改后端 API（已实现）
- 确保复制功能在所有浏览器正常工作
- 错误处理用户友好
- 结果展示支持滚动查看（当 Ad 数量较多时）

**_Leverage**:
- 参考 `design.md` 中的 ResultDisplay 组件设计
- 使用 Task 5.3 实现的 API 端点

**_Requirements**:
- US-011: 生成结果展示与复制

**Success**:
- 生成按钮正常工作
- 生成结果正确显示（1 个 Campaign Name、1 个 Ad Set Name、多个 Ad 结果）
- OneLink URL 数量与 Ad Name 数量完全一致
- 每个结果都有独立的复制按钮
- 复制功能正常工作，有视觉反馈
- 视觉反馈正确显示
- 加载状态正确显示
- 错误处理正确

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 7: 部署与 CI/CD

#### Task 7.1: 配置 Firebase Hosting 部署
- [x] **状态**: 已完成
- **文件**:
  - `frontend/firebase.json`
  - `frontend/.firebaserc`
  - `infra/github/workflows/frontend-deploy.yaml`
- **需求**: INT-004 (Firebase Hosting 集成)
- **描述**: 配置 Firebase Hosting、GitHub Actions 自动部署

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: DevOps Engineer

**Task**:
配置 Firebase Hosting 部署，包括 firebase.json 配置、GitHub Actions 工作流、环境变量配置。确保自动部署流程正常工作。

**Restrictions**:
- 不要修改后端部署配置（下一任务）
- 确保使用正确的 Firebase 项目
- 不要硬编码敏感信息

**_Leverage**:
- 参考 `design.md` 中的部署设计
- 参考 `requirements.md` 中的 INT-004

**_Requirements**:
- INT-004: Firebase Hosting 集成

**Success**:
- Firebase Hosting 配置正确
- GitHub Actions 工作流正常工作
- 自动部署成功
- 自定义域名配置正确（如需要）

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 7.2: 配置 Cloud Run 部署
- [x] **状态**: 已完成
- **文件**:
  - `backend/Dockerfile` (更新)
  - `infra/cloudbuild.yaml`
  - `infra/github/workflows/backend-deploy.yaml`
- **需求**: INT-005 (Cloud Run 集成)
- **描述**: 配置 Cloud Run 部署、Cloud Build、Artifact Registry

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: DevOps Engineer

**Task**:
配置 Cloud Run 部署，包括 Dockerfile 优化、Cloud Build 配置、Artifact Registry 推送、Cloud Run 部署配置、环境变量配置、健康检查配置。

**Restrictions**:
- 不要修改前端部署配置
- 确保使用正确的 GCP 项目
- 不要硬编码敏感信息（使用 Secret Manager）

**_Leverage**:
- 参考 `design.md` 中的部署设计
- 参考 `requirements.md` 中的 INT-005

**_Requirements**:
- INT-005: Cloud Run 集成

**Success**:
- Docker 镜像正确构建
- Cloud Build 配置正确
- Artifact Registry 推送成功
- Cloud Run 部署成功
- 环境变量正确配置
- 健康检查正常工作

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

### 阶段 8: 测试与优化

#### Task 8.1: 编写单元测试
- [ ] **状态**: 待开始
- **文件**:
  - `backend/tests/services/test_naming_service.py`
  - `backend/tests/services/test_onelink_service.py`
  - `backend/tests/utils/test_email.py`
  - `frontend/__tests__/utils/emailUtils.test.ts`
  - `frontend/__tests__/components/forms/CampaignForm.test.tsx`
- **需求**: NFR-005 (可维护性需求)
- **描述**: 编写关键业务逻辑和组件的单元测试

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Test Developer

**Task**:
编写单元测试，覆盖命名服务、OneLink 服务、工具函数、关键组件。确保测试覆盖率 > 80%。

**Restrictions**:
- 不要编写集成测试（下一任务）
- 确保测试独立运行
- 使用 Mock 避免外部依赖

**_Leverage**:
- 参考 `design.md` 中的测试设计
- 参考 `requirements.md` 中的 NFR-005

**_Requirements**:
- NFR-005: 可维护性需求

**Success**:
- 所有关键函数有单元测试
- 测试覆盖率 > 80%
- 所有测试通过
- 测试运行时间合理

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

#### Task 8.2: 编写集成测试和 E2E 测试
- [ ] **状态**: 待开始
- **文件**:
  - `backend/tests/api/test_generate.py`
  - `backend/tests/api/test_auth.py`
  - `frontend/__tests__/e2e/generation-flow.spec.ts` (Playwright)
- **需求**: NFR-005 (可维护性需求)
- **描述**: 编写 API 集成测试和端到端测试

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Test Developer

**Task**:
编写集成测试（API 端点测试）和端到端测试（完整用户流程测试）。使用 Playwright 进行 E2E 测试。

**Restrictions**:
- 不要修改业务逻辑
- 确保测试环境配置正确
- E2E 测试需要真实的后端环境

**_Leverage**:
- 参考 `design.md` 中的测试设计
- 参考 `requirements.md` 中的验收测试场景

**_Requirements**:
- NFR-005: 可维护性需求

**Success**:
- API 集成测试通过
- E2E 测试通过
- 测试覆盖主要用户流程
- 测试稳定可靠

**Instructions**:
1. 在 tasks.md 中将此任务状态从 `[ ]` 改为 `[-]` 表示开始
2. 完成实现后，将状态改为 `[x]` 表示完成

---

## 任务依赖关系

```
阶段 1 (初始化)
  ├─ Task 1.1 (前端初始化)
  ├─ Task 1.2 (后端初始化)
  └─ Task 1.3 (数据库配置)
      │
阶段 2 (认证)
  ├─ Task 2.1 (后端认证) ──┐
  └─ Task 2.2 (前端认证) ──┘
      │
阶段 3 (数据访问)
  ├─ Task 3.1 (Google Sheets) ──┐
  ├─ Task 3.2 (搜索 API) ────────┤
  └─ Task 3.3 (搜索组件) ────────┘
      │
阶段 4 (表单)
  ├─ Task 4.1 (Campaign 表单)
  ├─ Task 4.2 (Ad Set 表单)
  └─ Task 4.3 (Ad 表单)
      │
阶段 5 (命名规则)
  ├─ Task 5.1 (命名服务) ───┐
  ├─ Task 5.2 (OneLink 服务)─┤
  └─ Task 5.3 (生成 API) ────┘
      │
阶段 6 (前端生成)
  ├─ Task 6.1 (页面布局)
  └─ Task 6.2 (生成逻辑)
      │
阶段 7 (部署)
  ├─ Task 7.1 (Firebase)
  └─ Task 7.2 (Cloud Run)
      │
阶段 8 (测试)
  ├─ Task 8.1 (单元测试)
  └─ Task 8.2 (集成/E2E 测试)
```

---

## 阶段 9: Program Info 数据库同步 (US-010)

### Task 9.1: 创建 Program Info 数据库模型 [x]

**文件**: `backend/app/models/program_info.py`

**描述**: 创建 `ProgramInfo` SQLAlchemy 模型，字段与 Google Sheets 保持一致

**要求**:
- 使用 `program_code` 作为主键
- 包含所有字段：program_code, program_id, title, sub_title, synopsis, episode_count, release_date, content_information, program_shortner, title_en_shortener, season_id
- 添加 created_at 和 updated_at 时间戳字段
- 创建必要的索引（program_id, release_date, updated_at）
- 在 `backend/app/models/__init__.py` 中导出模型

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Database Developer

**Task**: Create the ProgramInfo SQLAlchemy model for storing Program Info data from Google Sheets. The model should match the ProgramInfo Pydantic schema fields exactly, with program_code as primary key. Include created_at and updated_at timestamp fields with automatic updates. Add indexes on program_id, release_date, and updated_at for query performance.

**Restrictions**: 
- Do not modify existing models
- Follow existing model patterns in the codebase
- Use async SQLAlchemy syntax
- Ensure all fields match the Pydantic schema exactly

**_Leverage**: 
- `backend/app/models/base.py` for Base class
- `backend/app/schemas/program.py` for field reference
- `backend/app/models/user.py` for model structure examples

**_Requirements**: US-010

**Success**: 
- Model file created with all required fields
- Model exported in `__init__.py`
- Database migration can be generated successfully
- All fields match ProgramInfo Pydantic schema

**Instructions**: 
1. Mark this task as in-progress [-] in tasks.md
2. Create the model file following existing patterns
3. Test model creation with database
4. Mark task as complete [x] when done

---

### Task 9.2: 实现 Program Sync Service [x]

**文件**: `backend/app/services/program_sync_service.py`

**描述**: 实现从 Google Sheets 同步数据到数据库的服务

**要求**:
- 从 Google Sheets 读取所有 Program Info 数据
- 与数据库现有数据对比，检测变化
- 执行增量更新（新增、更新、删除）
- 返回同步统计信息
- 处理错误和异常情况

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Service Developer

**Task**: Create ProgramSyncService that synchronizes Program Info data from Google Sheets to the database. The service should detect changes (new, updated, deleted records) and perform incremental updates. It should reuse GoogleSheetsService for reading data and use SQLAlchemy for database operations.

**Restrictions**: 
- Do not modify GoogleSheetsService
- Handle errors gracefully with logging
- Use async/await throughout
- Do not delete records that exist in database but not in sheets (soft delete approach)

**_Leverage**: 
- `backend/app/services/google_sheets_service.py` for reading from sheets
- `backend/app/models/program_info.py` for database model
- `backend/app/schemas/program.py` for data validation

**_Requirements**: US-010

**Success**: 
- Service can read from Google Sheets
- Service can detect changes between sheets and database
- Service can insert new records
- Service can update existing records
- Service returns sync statistics

**Instructions**: 
1. Mark this task as in-progress [-] in tasks.md
2. Implement the sync service with change detection
3. Test with sample data
4. Mark task as complete [x] when done

---

### Task 9.3: 实现定时同步任务 [x]

**文件**: `backend/app/core/scheduler.py`

**描述**: 使用 APScheduler 实现定时同步任务，在北京时间每天 9:00, 12:00, 18:00 执行

**要求**:
- 配置 APScheduler 使用 Asia/Shanghai 时区
- 设置三个定时任务（早上、中午、晚上）
- 在应用启动时启动调度器
- 在应用关闭时关闭调度器
- 添加日志记录

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Infrastructure Developer

**Task**: Set up APScheduler to run Program Info sync tasks at 9:00, 12:00, and 18:00 Beijing time (Asia/Shanghai timezone) daily. Integrate scheduler lifecycle with FastAPI application startup/shutdown.

**Restrictions**: 
- Use AsyncIOScheduler for async support
- Do not block application startup
- Handle scheduler errors gracefully
- Use proper timezone handling

**_Leverage**: 
- `backend/app/main.py` for lifespan integration
- `backend/app/services/program_sync_service.py` for sync logic
- APScheduler documentation for async scheduler setup

**_Requirements**: US-010

**Success**: 
- Scheduler starts with application
- Three cron jobs configured correctly
- Timezone set to Asia/Shanghai
- Scheduler shuts down gracefully
- Logs sync execution

**Instructions**: 
1. Mark this task as in-progress [-] in tasks.md
2. Install APScheduler if not already in requirements
3. Create scheduler module
4. Integrate with FastAPI lifespan
5. Test scheduler execution
6. Mark task as complete [x] when done

---

### Task 9.4: 创建手动同步 API 端点 [x]

**文件**: `backend/app/api/v1/admin.py` (新建)

**描述**: 创建管理员 API 端点，支持手动触发同步

**要求**:
- POST `/api/admin/sync/programs` 端点
- 返回同步结果统计
- 添加适当的错误处理
- 可选：添加认证/授权（未来扩展）

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend API Developer

**Task**: Create admin API endpoint for manually triggering Program Info sync. The endpoint should call ProgramSyncService and return sync statistics. Add proper error handling and response formatting.

**Restrictions**: 
- Use FastAPI router pattern
- Return structured JSON response
- Handle errors with appropriate HTTP status codes
- Do not add authentication yet (can be added later)

**_Leverage**: 
- `backend/app/api/v1/router.py` for router registration
- `backend/app/services/program_sync_service.py` for sync logic
- `backend/app/api/v1/programs.py` for API pattern reference

**_Requirements**: US-010

**Success**: 
- Endpoint created and registered
- Can trigger sync manually
- Returns sync statistics
- Handles errors properly

**Instructions**: 
1. Mark this task as in-progress [-] in tasks.md
2. Create admin router
3. Register endpoint
4. Test endpoint
5. Mark task as complete [x] when done

---

### Task 9.5: 重构 ProgramRepository 从数据库读取 [x]

**文件**: `backend/app/repositories/program_repository.py`

**描述**: 修改 ProgramRepository，将所有数据读取操作改为从数据库读取，而不是 Google Sheets

**要求**:
- `get_all_programs()` 从数据库读取
- `search_programs()` 使用 SQL 查询
- `list_programs()` 使用数据库分页
- 移除 Google Sheets 相关代码和缓存逻辑
- 保持 API 接口不变

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend Data Access Developer

**Task**: Refactor ProgramRepository to read from database instead of Google Sheets. Replace all Google Sheets API calls with SQLAlchemy queries. Remove caching logic since database is the source of truth. Maintain the same public API interface.

**Restrictions**: 
- Do not change method signatures
- Do not break existing API endpoints
- Use async SQLAlchemy queries
- Remove GoogleSheetsService dependency
- Keep error handling patterns

**_Leverage**: 
- `backend/app/models/program_info.py` for database model
- `backend/app/repositories/program_repository.py` for existing structure
- SQLAlchemy async query patterns

**_Requirements**: US-010

**Success**: 
- All methods read from database
- API endpoints still work
- Performance is acceptable
- No Google Sheets calls in repository

**Instructions**: 
1. Mark this task as in-progress [-] in tasks.md
2. Refactor repository methods
3. Test with existing API endpoints
4. Verify frontend still works
5. Mark task as complete [x] when done

---

### Task 9.6: 执行首次数据同步 [x]

**文件**: `backend/scripts/sync_programs.py` (新建脚本)

**描述**: 创建脚本执行首次数据同步，用于测试

**要求**:
- 独立的 Python 脚本
- 可以手动运行
- 显示同步进度和结果
- 处理错误并显示友好消息

**_Prompt**:
Implement the task for spec campaign-naming-generator, first run spec-workflow-guide to get the workflow guide then implement the task:

**Role**: Backend DevOps Developer

**Task**: Create a standalone script to perform initial Program Info sync from Google Sheets to database. The script should be runnable independently, show progress, and provide clear output about sync results.

**Restrictions**: 
- Script should be executable standalone
- Use async/await properly
- Handle database connection setup
- Provide clear console output
- Exit with appropriate status codes

**_Leverage**: 
- `backend/app/services/program_sync_service.py` for sync logic
- `backend/app/core/database.py` for database setup
- `backend/app/core/config.py` for configuration

**_Requirements**: US-010

**Success**: 
- Script can be run: `python scripts/sync_programs.py`
- Shows sync progress
- Displays final statistics
- Handles errors gracefully
- Database populated with data

**Instructions**: 
1. Mark this task as in-progress [-] in tasks.md
2. Create sync script
3. Test script execution
4. Verify data in database
5. Mark task as complete [x] when done

---

## 变更历史

| 日期 | 版本 | 变更说明 | 变更人 |
|------|------|----------|--------|
| 2025-01-11 | 1.0 | 初始版本 | AI Assistant |
| 2025-01-11 | 1.1 | 添加阶段 9: Program Info 数据库同步任务 | AI Assistant |

