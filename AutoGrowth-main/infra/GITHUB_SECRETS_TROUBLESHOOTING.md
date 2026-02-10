# GitHub Secrets 故障排查

## 错误信息

```
Error: google-github-actions/auth failed with: the GitHub Action workflow must specify exactly one of "workload_identity_provider" or "credentials_json"! If you are specifying input values via GitHub secrets, ensure the secret is being injected into the environment.
```

## 可能的原因

1. **GitHub Secret 不存在或为空**
   - Secret `GCP_SA_KEY` 可能未创建
   - Secret 值为空

2. **Secret 名称不匹配**
   - Workflow 中使用 `GCP_SA_KEY`，但 GitHub 中可能使用了不同的名称

3. **Secret 权限问题**
   - Secret 可能没有正确配置权限

## 解决方案

### 步骤 1: 验证 GitHub Secrets

1. 访问 GitHub 仓库: https://github.com/lijiannan828-oss/AutoGrowth
2. 点击 **Settings** > **Secrets and variables** > **Actions**
3. 确认以下 Secrets 存在且不为空：
   - ✅ `GCP_SA_KEY` - GCP 服务账号 JSON 密钥
   - ✅ `POSTGRES_PASSWORD` - 数据库密码
   - ✅ `CLOUD_SQL_CONN_NAME` - Cloud SQL 连接名称（可选，已在 workflow 中硬编码）
   - ✅ `FIREBASE_AUTOGROWTH_PROJECT_ID` - GCP 项目 ID（可选，已在 workflow 中硬编码）
   - ✅ `GOOGLE_SHEETS_ID` - Google Sheets ID（可选）

### 步骤 2: 检查 Secret 值格式

`GCP_SA_KEY` 应该是完整的 JSON 格式，例如：

```json
{
  "type": "service_account",
  "project_id": "autogrowth-477909",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com",
  ...
}
```

### 步骤 3: 验证 Workflow 语法

确保 workflow 文件中正确引用了 secret：

```yaml
- name: Authenticate to Google Cloud
  id: auth
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

### 步骤 4: 添加调试信息（临时）

如果问题仍然存在，可以在 workflow 中添加调试步骤来检查 secret 是否存在：

```yaml
- name: Debug - Check if secret exists
  run: |
    if [ -z "${{ secrets.GCP_SA_KEY }}" ]; then
      echo "❌ GCP_SA_KEY secret is empty or not set"
      exit 1
    else
      echo "✅ GCP_SA_KEY secret exists (length: ${#GCP_SA_KEY})"
    fi
```

## 常见问题

### Q: Secret 存在但 workflow 仍然失败？

**A**: 检查：
1. Secret 名称是否完全匹配（区分大小写）
2. Secret 值是否包含有效的 JSON
3. 是否有特殊字符需要转义

### Q: 如何重新创建 Secret？

**A**:
1. 删除旧的 Secret
2. 创建新的 Secret，确保：
   - 名称完全匹配：`GCP_SA_KEY`
   - 值是完整的 JSON 格式
   - 没有多余的空格或换行

### Q: 可以使用 Workload Identity 吗？

**A**: 可以，但需要额外配置。当前使用 `credentials_json` 更简单直接。

## 验证步骤

1. ✅ 确认 Secret 存在
2. ✅ 确认 Secret 值不为空
3. ✅ 确认 Secret 名称匹配
4. ✅ 重新运行 workflow






