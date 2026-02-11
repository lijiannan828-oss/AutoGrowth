# 重启后端服务指南

## 问题
数据库连接成功后，前端仍然刷不到数据，可能是因为：
1. 后端服务在数据库连接配置更新前启动
2. 后端服务启动时数据库连接失败，fallback到"Google Sheets only"模式
3. 需要重启服务以使用新的数据库配置

## 解决方案

### 1. 停止当前后端服务

找到正在运行的后端服务进程并停止：

```bash
# 查找进程
ps aux | grep uvicorn | grep -v grep

# 停止进程（替换 PID 为实际进程ID）
kill <PID>

# 或者强制停止
kill -9 <PID>
```

### 2. 设置环境变量

确保设置了正确的数据库连接环境变量：

```bash
cd backend
source venv/bin/activate

export CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
export DATABASE_NAME=auto_growth
export DATABASE_USER=appdev  # 或 appprod
export DATABASE_PASSWORD="930828Krisrita*"
export USE_IAM_AUTH=false
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

### 3. 重启后端服务

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 验证连接

查看启动日志，应该看到：
```
✅ Database connection initialized
```

如果看到：
```
⚠️  Database connection failed (will use Google Sheets only): ...
```

说明数据库连接仍有问题，需要检查配置。

### 5. 测试API

```bash
curl 'http://localhost:8000/api/data/programs?page=1&page_size=5'
```

应该返回数据。

## 注意事项

- 后端服务使用 `--reload` 参数时，代码更改会自动重启，但环境变量更改需要手动重启
- 如果使用 `.env` 文件，确保文件存在且格式正确
- 数据库连接在应用启动时初始化，如果启动时失败，会fallback到Google Sheets only模式

