# Cloud SQL Connector 设置说明

## 已完成的工作

1. ✅ 添加了 `cloud-sql-python-connector[asyncpg]>=1.18.0` 到 `requirements.txt`
2. ✅ 更新了 `app/core/config.py` 添加 Cloud SQL 连接配置
3. ✅ 更新了 `app/core/database.py` 使用 Cloud SQL Connector
4. ✅ 更新了 `app/main.py` 在应用启动时自动初始化数据库连接
5. ✅ 已停止 cloud_sql_proxy（不再需要）

## 环境变量配置

在 `.env` 文件中添加：

```env
CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
DATABASE_NAME=auto_growth
DATABASE_USER=postgres
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

## 当前状态

- ✅ Cloud SQL Connector 已安装
- ✅ 代码已更新使用 Cloud SQL Connector
- ⚠️ 需要解决 event loop 匹配问题

## 待解决的问题

SQLAlchemy 的 greenlet 机制与 Cloud SQL Connector 的 event loop 要求存在冲突。需要进一步调整实现方式。

## 临时解决方案

如果 Cloud SQL Connector 集成有问题，系统会自动降级为：
1. 直接使用 Google Sheets（无缓存）
2. 或使用 DATABASE_URL 直接连接（如果配置了）

系统仍然可以正常工作，只是没有数据库缓存功能。






