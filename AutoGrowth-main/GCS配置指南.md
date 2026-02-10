# Google Cloud Storage (GCS) 配置指南

## 问题：裂变功能上传视频失败

**原因**：裂变功能需要上传视频到 Google Cloud Storage (GCS)，但缺少 GCS 凭证配置。

---

## 配置步骤

### 1. 获取 Google Cloud 服务账号密钥

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 选择你的项目（或创建新项目）
3. 导航到：**IAM & Admin** → **Service Accounts**
4. 创建服务账号或选择现有账号
5. 点击 **Keys** → **Add Key** → **Create new key**
6. 选择 **JSON** 格式
7. 下载 JSON 密钥文件（例如：`service-account-key.json`）

### 2. 创建 GCS 存储桶

1. 在 Google Cloud Console 中，导航到 **Cloud Storage** → **Buckets**
2. 点击 **Create Bucket**
3. 输入存储桶名称（例如：`vigloo-fission-uploads`）
4. 选择区域（建议：`us-central1`）
5. 点击 **Create**

### 3. 配置后端环境变量

在 `backend/.env` 文件中添加以下配置：

```env
# Google Cloud 配置
GOOGLE_APPLICATION_CREDENTIALS=D:/path/to/your/service-account-key.json
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1

# Fission 存储桶配置
FISSION_UPLOAD_BUCKET=vigloo-fission-uploads
FISSION_BUCKET=vigloo_source
```

**重要**：
- `GOOGLE_APPLICATION_CREDENTIALS` 必须是 **绝对路径**
- 路径使用 `/` 而不是 `\`（Windows 也可以用 `/`）
- 确保服务账号有存储桶的读写权限

### 4. 验证配置

启动后端后，访问测试接口：

```
http://localhost:8001/api/v1/fission/test-gcs
```

如果配置正确，会返回：
```json
{
  "status": "success",
  "credentials_path": "D:/path/to/your/service-account-key.json",
  "bucket_name": "vigloo-fission-uploads",
  "video_count": 0,
  "sample_videos": []
}
```

如果配置错误，会返回错误信息。

---

## 常见问题

### Q1: 提示 "Could not automatically determine credentials"
**解决**：检查 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量是否设置正确，路径是否存在。

### Q2: 提示 "403 Forbidden"
**解决**：服务账号缺少权限，需要在 GCS 存储桶中添加服务账号，并授予 **Storage Object Admin** 角色。

### Q3: 提示 "Bucket does not exist"
**解决**：检查存储桶名称是否正确，或者创建对应的存储桶。

---

## 临时解决方案（不推荐）

如果暂时无法配置 GCS，可以使用本地上传（功能受限）：

前端修改 `handleUpload` 函数，使用 `/fission/upload` 接口（本地存储）。

但这样无法使用 Cloud Run 等云服务进行视频处理。

