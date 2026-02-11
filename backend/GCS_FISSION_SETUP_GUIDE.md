# AI 裂变素材生成 - GCS 配置指南

## 🔍 问题诊断

你遇到的问题是：**AI 裂变素材生成的上传视频功能无法使用，但多语言字幕生成的上传功能正常**

### 原因分析

1. **多语言字幕生成** 使用的是 **本地文件上传**（直接上传到后端服务器）
   - 代码位置：`frontend/src/app/subtitle/page.tsx` 第 124 行
   - 使用 `FormData` 直接上传到 `/api/v1/subtitle/upload`
   - **不需要 GCS 配置**

2. **AI 裂变素材生成** 使用的是 **GCS 签名 URL 上传**（直接上传到 Google Cloud Storage）
   - 代码位置：`frontend/src/app/fission/page.tsx` 第 286-333 行
   - 流程：前端 → 后端获取签名 URL → 前端直接上传到 GCS
   - **需要完整的 GCS 配置**

---

## ⚠️ 根本原因：缺少 Service Account 密钥文件

**检查结果：你的 backend 目录下没有 Service Account JSON 密钥文件！**

这就是为什么无法上传的根本原因。

---

## 📋 解决方案：获取 Service Account 密钥文件

### 步骤 1：从 Google Cloud Console 下载密钥

1. 访问 [Google Cloud Console - Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts?project=fleet-blend-469520-n7)

2. 找到你的 Service Account（可能是类似这样的名称）：
   - `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`
   - 或其他有权限的 Service Account

3. 点击 Service Account 进入详情页

4. 切换到 **"密钥"** 标签页

5. 点击 **"添加密钥"** → **"创建新密钥"**

6. 选择 **JSON** 格式

7. 点击 **"创建"**，密钥文件会自动下载到你的电脑

### 步骤 2：将密钥文件放到正确位置

1. 将下载的 JSON 文件重命名为：`service-account.json`

2. 将文件复制到：
   ```
   d:\AutoGrowth-main (1)\AutoGrowth-main\backend\service-account.json
   ```

### 步骤 3：更新 .env 文件

打开 `backend\.env` 文件，确保这一行指向正确的文件：
```env
GOOGLE_APPLICATION_CREDENTIALS=d:\AutoGrowth-main (1)\AutoGrowth-main\backend\service-account.json
```

---

## 🔐 Service Account 需要的权限

确保你的 Service Account 有以下权限：

1. **Storage Admin** (roles/storage.admin) 或
2. **Storage Object Admin** (roles/storage.objectAdmin)
3. **Firestore User** (roles/datastore.user) - 用于存储任务信息

### 如何检查和添加权限

1. 访问 [IAM 页面](https://console.cloud.google.com/iam-admin/iam?project=fleet-blend-469520-n7)

2. 找到你的 Service Account

3. 点击编辑（铅笔图标）

4. 点击 **"添加其他角色"**

5. 搜索并添加上述角色

6. 点击 **"保存"**

### 2. 环境变量配置

我已经帮你更新了 `.env` 文件，添加了以下配置：

```env
# GCP 项目配置
GCP_PROJECT_ID=fleet-blend-469520-n7
GCP_REGION=us-central1

# Firestore 配置
FIRESTORE_PROJECT_ID=fleet-blend-469520-n7
FIRESTORE_DATABASE=(default)

# GCS 存储桶配置（AI 裂变素材生成）
FISSION_BUCKET=vigloo-fission-outputs
FISSION_UPLOAD_BUCKET=vigloo-fission-uploads
```

---

## 需要创建的 GCS 存储桶

你需要在 Google Cloud Console 中创建两个存储桶：

### 方法 1：使用 Google Cloud Console（推荐）

1. 访问 [Google Cloud Console - Storage](https://console.cloud.google.com/storage)
2. 选择项目：`fleet-blend-469520-n7`
3. 点击 "创建存储桶"
4. 创建以下两个存储桶：

#### 存储桶 1：上传桶
- **名称**：`vigloo-fission-uploads`
- **位置类型**：Region
- **位置**：`us-central1`（与你的 GCP_REGION 一致）
- **存储类别**：Standard
- **访问控制**：统一（推荐）
- **保护工具**：无（或根据需要）

#### 存储桶 2：输出桶
- **名称**：`vigloo-fission-outputs`
- **位置类型**：Region
- **位置**：`us-central1`
- **存储类别**：Standard
- **访问控制**：统一（推荐）
- **保护工具**：无（或根据需要）

### 方法 2：使用 gcloud 命令行

```bash
# 设置项目
gcloud config set project fleet-blend-469520-n7

# 创建上传桶
gsutil mb -p fleet-blend-469520-n7 -c STANDARD -l us-central1 gs://vigloo-fission-uploads

# 创建输出桶
gsutil mb -p fleet-blend-469520-n7 -c STANDARD -l us-central1 gs://vigloo-fission-outputs
```

---

## 验证配置

### 1. 检查 Service Account 权限

确保你的 Service Account 有以下权限：
- **Storage Object Admin** (roles/storage.objectAdmin)
- **Storage Admin** (roles/storage.admin) 或
- 至少对这两个存储桶有读写权限

### 2. 测试 GCS 连接

重启后端服务后，访问以下 API 测试连接：

```bash
# 测试 GCS 连接
curl http://localhost:8000/api/v1/fission/videos
```

应该返回类似：
```json
{
  "status": "success",
  "credentials_path": "d:\\AutoGrowth-main (1)\\AutoGrowth-main\\backend\\fleet-blend-469520-n7-23b7c649292b.json",
  "bucket_name": "vigloo-fission-uploads",
  "video_count": 0,
  "sample_videos": []
}
```

---

## 重启后端服务

配置完成后，需要重启后端服务以加载新的环境变量：

```powershell
# 停止当前运行的后端
# 按 Ctrl+C 停止

# 重新启动
cd "d:\AutoGrowth-main (1)\AutoGrowth-main\backend"
.\start_backend.ps1
```

---

## 常见问题排查

### 问题 1：上传时提示 "生成上传URL失败"

**原因**：
- Service Account 没有权限
- 存储桶不存在
- 环境变量未正确加载

**解决方法**：
1. 检查存储桶是否存在
2. 检查 Service Account 权限
3. 重启后端服务

### 问题 2：上传成功但创建任务失败

**原因**：
- Firestore 未配置
- 源视频路径格式错误

**解决方法**：
1. 确保 `FIRESTORE_PROJECT_ID` 已配置
2. 检查视频路径格式：`gs://vigloo-fission-uploads/xxx.mp4`

### 问题 3：如何查看后端日志

```powershell
# 查看后端终端输出
# 应该能看到类似的日志：
# [INFO] GCS Client initialized successfully
# [INFO] Firestore Client initialized
```

---

## 下一步

1. ✅ 环境变量已配置（我已帮你完成）
2. ⏳ 创建 GCS 存储桶（需要你在 Google Cloud Console 操作）
3. ⏳ 重启后端服务
4. ⏳ 测试上传功能

完成这些步骤后，AI 裂变素材生成的上传功能就可以正常使用了！

---

## 已添加的环境变量说明

我已经将以下关键配置添加到你的 `.env` 文件中：

### 🔑 AI 裂变素材生成必需配置
```env
GCP_PROJECT_ID=fleet-blend-469520-n7          # GCP 项目 ID
GCP_REGION=us-central1                         # GCP 区域
FIRESTORE_PROJECT_ID=fleet-blend-469520-n7     # Firestore 项目 ID
FIRESTORE_DATABASE=(default)                   # Firestore 数据库名
FISSION_BUCKET=vigloo-fission-outputs          # 输出存储桶
FISSION_UPLOAD_BUCKET=vigloo-fission-uploads   # 上传存储桶
```

### 📋 其他已保留的配置
- Google OAuth 配置（用于登录和 Pipeline 功能）
- Pipeline 配置（资源流水线功能）
- Google Sheets 配置
- 数据库配置

### ⚠️ 注意事项
- `GOOGLE_OAUTH_REDIRECT_URI` 已改为本地开发地址：`http://localhost:3001/login`
- 如果需要使用生产环境，请改回：`https://autogrowth-477909.web.app/login`

