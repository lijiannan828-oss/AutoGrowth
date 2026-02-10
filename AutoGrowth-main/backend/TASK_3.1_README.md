# Task 3.1: Google Sheets 集成 - 实现说明

## 已完成的工作

### 1. 依赖配置
- ✅ 添加 `gspread==6.1.4` 和 `google-api-python-client==2.152.0` 到 `requirements.txt`
- ✅ 更新 `.env.example` 添加 `GOOGLE_SHEETS_ID` 配置

### 2. 代码实现

#### 配置文件
- ✅ `backend/app/core/config.py`: 添加 `google_sheets_id` 配置项

#### Google Sheets 客户端
- ✅ `backend/app/core/google_sheets.py`: 实现 gspread 客户端初始化，使用服务账号凭证

#### 数据模型
- ✅ `backend/app/schemas/program.py`: 定义 `ProgramInfo` Pydantic 模型
  - `program_code` (ProgramCode)
  - `program_id` (id)
  - `title` (英文标题)
  - `episode_count` (Total Episode No.)

#### 服务层
- ✅ `backend/app/services/google_sheets_service.py`: 实现 `GoogleSheetsService`
  - 从 "All" sheet 读取: ProgramCode, id, episodeCount
  - 从 "En" sheet 读取: ProgramCode, Title
  - 通过 ProgramCode 合并数据
  - 实现 `get_all_programs()` 和 `search_programs()` 方法

#### 仓储层
- ✅ `backend/app/repositories/program_repository.py`: 实现 `ProgramRepository`
  - 集成 Google Sheets 服务
  - 实现缓存机制（5分钟 TTL）
  - 支持从缓存或 Google Sheets 获取数据
  - 实现搜索功能

### 3. 测试脚本
- ✅ `backend/test_google_sheets.py`: 创建测试脚本用于验证连接

## 下一步操作

### 1. 安装依赖
由于网络问题，需要手动安装依赖：

```bash
cd backend
source venv/bin/activate
pip install gspread==6.1.4 google-api-python-client==2.152.0
```

### 2. 配置环境变量
确保 `backend/.env` 文件包含：

```env
GOOGLE_SHEETS_ID=1XzfHS7jasnlQpw54-oLgJxqAltbP9b8OtnMCr8SFPPI
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

### 3. 测试连接
运行测试脚本：

```bash
cd backend
source venv/bin/activate
python test_google_sheets.py
```

## 数据字段映射

根据用户需求，从 Google Sheets 读取以下字段：

| 字段名 | 来源 Sheet | Google Sheets 列名 | ProgramInfo 属性 |
|--------|-----------|-------------------|-----------------|
| ProgramCode | All | ProgramCode | program_code |
| Program ID | All | id | program_id |
| 英文标题 | En | Title (通过 ProgramCode 匹配) | title |
| 总集数 | All | episodeCount | episode_count |

## 注意事项

1. **服务账号权限**: 确保 `service-account.json` 中的服务账号已被授予对 Google Sheets 的访问权限
2. **Sheet 名称**: 代码假设存在 "All" 和 "En" 两个工作表
3. **数据合并**: 如果 "En" sheet 中找不到对应的 ProgramCode，该记录将被跳过
4. **缓存**: 缓存机制需要数据库连接，如果数据库未配置，缓存功能将自动降级为直接读取 Google Sheets

## 待完成（后续任务）

- [ ] 实现 API 端点（Task 3.2）
- [ ] 实现前端列表组件（Task 3.3）
- [ ] 实现搜索功能（Task 3.4）
