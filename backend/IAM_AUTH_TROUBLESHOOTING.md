# IAM 认证问题排查

## 当前状态

✅ **已完成：**
- IAM 数据库用户已创建：`sa-dev@fleet-blend-469520-n7.iam`
- 服务账号有 `roles/cloudsql.client` 权限
- Cloud SQL 实例已启用 IAM 认证
- 代码已配置使用 IAM 认证

❌ **问题：**
- 连接时出现错误：`Cloud SQL IAM service account authentication failed`

## 可能的原因和解决方案

### 1. IAM 数据库用户需要被授予数据库权限

IAM 数据库用户创建后，需要被授予数据库和表的权限。由于无法直接连接数据库，可以尝试以下方法：

**方法 A：使用 Cloud SQL Proxy 连接并授予权限**

```bash
# 启动 Cloud SQL Proxy
./cloud_sql_proxy -instances=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod=tcp:5432 \
  -credential_file=backend/service-account.json

# 在另一个终端连接（如果有其他用户可用）
psql -h 127.0.0.1 -p 5432 -U appdev -d auto_growth

# 然后执行权限授予
\c auto_growth
GRANT ALL PRIVILEGES ON DATABASE auto_growth TO "sa-dev@fleet-blend-469520-n7.iam";
GRANT ALL PRIVILEGES ON SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "sa-dev@fleet-blend-469520-n7.iam";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "sa-dev@fleet-blend-469520-n7.iam";
```

**方法 B：等待 IAM 用户生效**

有时 IAM 数据库用户创建后需要几分钟才能生效。可以等待 5-10 分钟后再次测试。

### 2. 检查服务账号的 IAM 角色绑定

确保服务账号有正确的 IAM 角色：

```bash
gcloud projects get-iam-policy fleet-blend-469520-n7 \
  --flatten="bindings[].members" \
  --filter="bindings.members:sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
```

应该看到 `roles/cloudsql.client` 角色。

### 3. 检查 Cloud SQL 实例的 IAM 设置

确保实例已启用 IAM 数据库认证：

```bash
gcloud sql instances describe yvideo-factory-db-prod \
  --format="get(settings.databaseFlags)"
```

应该看到 `cloudsql.iam_authentication: on`。

### 4. 尝试使用不同的用户名格式

有时需要使用完整的服务账号邮箱（带 `.gserviceaccount.com`）：

```bash
export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
```

或者使用不带后缀的格式（当前使用的）：

```bash
export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam"
```

## 测试连接

运行测试脚本：

```bash
cd backend
source venv/bin/activate
export CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
export DATABASE_NAME=auto_growth
export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam"
export USE_IAM_AUTH=true
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
python test_database_connection.py
```

## 下一步

1. **尝试使用 Cloud SQL Proxy 连接并授予权限**（如果 `appdev` 用户可用）
2. **等待 5-10 分钟**，然后再次测试（IAM 用户可能需要时间生效）
3. **检查 Cloud SQL 日志**，查看是否有更多错误信息

## 参考文档

- [Cloud SQL IAM 数据库用户](https://cloud.google.com/sql/docs/postgres/iam-authentication)
- [Cloud SQL Python Connector](https://cloud.google.com/sql/docs/postgres/connect-connectors#python)

