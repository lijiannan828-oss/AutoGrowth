# Cloud SQL 数据库连接设置指南

## 当前状态

✅ **已完成：**
- 已配置 Cloud SQL Python Connector
- 已修复 event loop 匹配问题
- 已创建测试脚本
- 已启用 IAM 认证支持

⚠️ **待解决：**
- 数据库连接认证失败

## 配置信息

- **实例连接名称**: `fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`
- **数据库名称**: `auto_growth`
- **服务账号**: `sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com`
- **服务账号文件**: `backend/service-account.json`

## 问题诊断

当前连接失败，错误信息：`password authentication failed`

可能的原因：
1. **IAM 数据库用户未创建**：如果使用 IAM 认证，需要在 Cloud SQL 中创建 IAM 数据库用户
2. **服务账号权限不足**：服务账号需要 `Cloud SQL Client` 角色
3. **用户名不正确**：可能需要使用 IAM 数据库用户而不是 `postgres`

## 解决步骤

### 选项 1：使用 IAM 数据库用户（推荐，当密码未启用时）

1. **在 Cloud SQL 中创建 IAM 数据库用户**：
   ```sql
   -- 连接到 Cloud SQL 实例（使用 gcloud 或其他方式）
   CREATE USER "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
   GRANT ALL PRIVILEGES ON DATABASE auto_growth TO "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
   ```

2. **验证服务账号权限**：
   ```bash
   # 确保服务账号有 Cloud SQL Client 角色
   gcloud projects get-iam-policy fleet-blend-469520-n7 \
     --flatten="bindings[].members" \
     --filter="bindings.members:sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
   ```

3. **配置环境变量**：
   ```bash
   export CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
   export DATABASE_NAME=auto_growth
   export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
   export USE_IAM_AUTH=true
   export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
   ```

4. **运行测试**：
   ```bash
   cd backend
   source venv/bin/activate
   python test_database_connection.py
   ```

### 选项 2：使用传统用户（如果密码实际上已设置）

如果数据库实际上有密码，但您说"未启用"，可能需要：

1. **获取数据库密码**（如果有）
2. **使用 DATABASE_URL**：
   ```bash
   export DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@/auto_growth?host=/cloudsql/fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod"
   ```

### 选项 3：检查 Cloud SQL 实例配置

1. **验证实例是否运行**：
   ```bash
   gcloud sql instances describe yvideo-factory-db-prod
   ```

2. **检查数据库用户**：
   ```bash
   gcloud sql users list --instance=yvideo-factory-db-prod
   ```

3. **检查 IAM 数据库用户**：
   ```bash
   gcloud sql users list --instance=yvideo-factory-db-prod --filter="type=CLOUD_IAM_SERVICE_ACCOUNT"
   ```

## 测试连接

运行测试脚本：
```bash
cd backend
source venv/bin/activate
python test_database_connection.py
```

## 代码配置

当前代码支持两种认证方式：

1. **IAM 认证**（`USE_IAM_AUTH=true`）：
   - 使用服务账号邮箱作为数据库用户名
   - 需要 IAM 数据库用户在 Cloud SQL 中创建

2. **传统认证**（`USE_IAM_AUTH=false`）：
   - 使用配置的用户名（默认 `postgres`）
   - 需要密码或 Cloud SQL Connector 的自动认证

## 下一步

请确认以下信息：

1. **IAM 数据库用户是否已创建？**
   - 如果已创建，用户名是什么？
   - 如果未创建，需要我提供创建命令吗？

2. **服务账号权限**：
   - 服务账号是否有 `Cloud SQL Client` 角色？
   - 是否有其他必要的权限？

3. **数据库用户信息**：
   - 除了 `postgres`，是否有其他可用的数据库用户？
   - 这些用户是否有密码？

## 参考文档

- [Cloud SQL Python Connector 文档](https://cloud.google.com/sql/docs/postgres/connect-connectors#python)
- [IAM 数据库用户](https://cloud.google.com/sql/docs/postgres/iam-authentication)
- [Cloud SQL 连接方式](https://cloud.google.com/sql/docs/postgres/connect-overview)

