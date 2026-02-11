# 前端数据不显示问题排查指南

## 问题现象
前端页面显示"已加载 0/0 个剧目"，但后端API正常返回数据（359条记录）。

## 排查步骤

### 1. 检查浏览器控制台
打开浏览器开发者工具（F12），查看：
- **Console** 标签：是否有 JavaScript 错误
- **Network** 标签：检查 `/api/data/programs` 请求
  - 请求是否发送成功
  - 响应状态码是否为 200
  - 响应数据格式是否正确

### 2. 检查 API 响应格式
后端返回格式：
```json
{
  "items": [...],
  "total": 359,
  "page": 1,
  "pageSize": 5
}
```

### 3. 检查前端代码
- `frontend/src/hooks/useProgramList.ts` - 数据获取逻辑
- `frontend/src/lib/api-client.ts` - API 客户端配置
- `frontend/src/types/api.ts` - 类型定义

### 4. 常见问题

#### 问题1: API 请求失败
**症状**: Network 标签显示请求失败（红色）
**解决**: 
- 检查后端服务是否运行：`curl http://localhost:8000/health`
- 检查 CORS 配置
- 检查 API URL 配置：`NEXT_PUBLIC_API_URL=http://localhost:8000/api`

#### 问题2: 数据格式不匹配
**症状**: 请求成功但数据为空
**解决**: 
- 检查 `ProgramInfo` 类型定义是否与后端返回的字段名匹配
- 检查字段名大小写（后端使用驼峰命名：`pageSize`，不是 `page_size`）

#### 问题3: React Query 缓存问题
**症状**: 数据加载一次后不再更新
**解决**: 
- 清除浏览器缓存
- 检查 React Query 的 `staleTime` 和 `gcTime` 配置
- 尝试硬刷新（Ctrl+Shift+R 或 Cmd+Shift+R）

### 5. 手动测试 API
```bash
# 测试后端 API
curl 'http://localhost:8000/api/data/programs?page=1&page_size=5'

# 测试前端页面
curl 'http://localhost:3000'
```

### 6. 检查环境变量
确保 `.env.local` 或 `.env` 文件存在且包含：
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### 7. 重启服务
如果以上都正常，尝试重启：
```bash
# 停止前端服务
# 然后重新启动
cd frontend && npm run dev

# 停止后端服务
# 然后重新启动
cd backend && uvicorn app.main:app --reload
```

## 调试命令

### 检查后端服务
```bash
curl http://localhost:8000/health
curl 'http://localhost:8000/api/data/programs?page=1&page_size=5'
```

### 检查前端服务
```bash
curl http://localhost:3000
```

### 检查进程
```bash
# 检查后端进程
ps aux | grep uvicorn

# 检查前端进程
ps aux | grep next
```

