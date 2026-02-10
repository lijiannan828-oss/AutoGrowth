# 创建 IAM 数据库用户指南

## 什么是 IAM 数据库用户？

IAM 数据库用户是 Cloud SQL PostgreSQL 中的特殊用户类型，允许使用 Google Cloud IAM 服务账号进行身份验证，而无需传统密码。

## 创建步骤

### 方法 1：使用 gcloud 命令（推荐）

```bash
gcloud sql users create "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --instance=yvideo-factory-db-prod \
  --type=CLOUD_IAM_SERVICE_ACCOUNT
```

### 方法 2：使用 SQL 命令

如果您能通过其他方式连接到数据库（例如使用 Cloud SQL Proxy 或其他用户），可以执行：

```sql
-- 连接到 auto_growth 数据库
\c auto_growth

-- 创建 IAM 数据库用户
CREATE USER "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE auto_growth TO "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com";
```

### 方法 3：使用 Cloud Console

1. 打开 [Google Cloud Console](https://console.cloud.google.com/sql/instances)
2. 选择实例 `yvideo-factory-db-prod`
3. 点击 "Users" 标签
4. 点击 "Add user account"
5. 选择 "Cloud IAM service account"
6. 输入服务账号邮箱：`sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com`
7. 点击 "Add"

## 验证 IAM 数据库用户

创建后，可以验证用户是否存在：

```bash
gcloud sql users list --instance=yvideo-factory-db-prod --filter="type=CLOUD_IAM_SERVICE_ACCOUNT"
```

或者使用 SQL：

```sql
SELECT usename, usecreatedb, usesuper 
FROM pg_user 
WHERE usename LIKE '%iam.gserviceaccount.com%';
```

## 使用 IAM 数据库用户连接

创建 IAM 数据库用户后，使用以下配置连接：

```bash
export CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
export DATABASE_NAME=auto_growth
export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
export USE_IAM_AUTH=true
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

## 注意事项

1. **用户名格式**：IAM 数据库用户名必须是完整的服务账号邮箱
2. **权限**：确保服务账号有 `Cloud SQL Client` 角色
3. **实例配置**：确保 Cloud SQL 实例已启用 IAM 数据库认证（通常在创建实例时已启用）

## 如果 appdev 是 IAM 用户

如果 `appdev` 用户已经配置为 IAM 数据库用户，可以直接使用：

```bash
export DATABASE_USER=appdev
export USE_IAM_AUTH=true
```

