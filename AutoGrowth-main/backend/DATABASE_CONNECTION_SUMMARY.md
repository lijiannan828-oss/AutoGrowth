# 数据库连接问题总结

## 当前状态

✅ **已完成：**
- Cloud SQL Python Connector 已配置
- Event loop 问题已修复
- 代码支持 IAM 和传统认证
- 默认用户设置为 `appdev`

❌ **问题：**
- 所有连接尝试都失败，错误：`password authentication failed`

## 问题分析

根据测试结果，无论使用哪种配置都失败，这表明：

1. **如果使用 IAM 认证**：需要在 Cloud SQL 中先创建 IAM 数据库用户
2. **如果使用传统认证**：`appdev` 用户可能需要密码，或者不是 IAM 用户

## 解决方案

### 方案 1：创建 IAM 数据库用户（推荐，当密码未启用时）

如果数据库密码确实未启用，应该使用 IAM 认证。需要先在 Cloud SQL 中创建 IAM 数据库用户：

```bash
# 使用 gcloud 创建 IAM 数据库用户
gcloud sql users create "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --instance=yvideo-factory-db-prod \
  --type=CLOUD_IAM_SERVICE_ACCOUNT
```

创建后，使用以下配置连接：

```bash
export CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
export DATABASE_NAME=auto_growth
export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
export USE_IAM_AUTH=true
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

### 方案 2：使用 appdev 用户（如果已有密码）

如果 `appdev` 用户实际上有密码，可以：

1. 获取密码
2. 使用 `DATABASE_URL` 连接（不推荐，因为您说密码未启用）

### 方案 3：检查 appdev 用户类型

请确认 `appdev` 用户：
- 是传统用户（需要密码）？
- 还是 IAM 数据库用户（已配置为 IAM 认证）？

如果是 IAM 数据库用户，应该可以直接使用：

```bash
export DATABASE_USER=appdev
export USE_IAM_AUTH=true
```

## 下一步操作

**请执行以下命令创建 IAM 数据库用户：**

```bash
gcloud sql users create "sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --instance=yvideo-factory-db-prod \
  --type=CLOUD_IAM_SERVICE_ACCOUNT
```

创建成功后，运行测试：

```bash
cd backend
source venv/bin/activate
export CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
export DATABASE_NAME=auto_growth
export DATABASE_USER="sa-dev@fleet-blend-469520-n7.iam.gserviceaccount.com"
export USE_IAM_AUTH=true
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
python test_database_connection.py
```

## 参考文档

详细步骤请查看：
- `CREATE_IAM_DATABASE_USER.md` - IAM 数据库用户创建指南
- `DATABASE_CONNECTION_SETUP.md` - 完整设置说明

