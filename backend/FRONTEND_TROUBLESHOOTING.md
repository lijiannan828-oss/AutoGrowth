# 前端数据不显示问题排查与解决

## 问题总结
前端页面显示"已加载 0/0 个剧目"，但后端API正常返回数据（359条记录）。

## 已完成的检查

### ✅ 后端服务
- 后端服务正常运行在 `http://localhost:8000`
- API 端点 `/api/data/programs` 正常返回数据
- 总记录数：359条
- CORS 配置正确

### ✅ 前端服务
- 前端服务正常运行在 `http://localhost:3000`
- Next.js 开发服务器正常

### ⚠️ 发现的问题
1. **环境变量文件缺失**：前端 `.env.local` 文件不存在
   - **已解决**：已创建 `.env.local` 文件，设置 `NEXT_PUBLIC_API_URL=http://localhost:8000/api`

## 下一步操作

### 1. 重启前端服务
环境变量更改后，需要重启前端服务才能生效：

```bash
# 停止当前前端服务（Ctrl+C）
# 然后重新启动
cd frontend
npm run dev
```

### 2. 清除浏览器缓存
- 硬刷新页面：`Ctrl+Shift+R` (Windows/Linux) 或 `Cmd+Shift+R` (Mac)
- 或者清除浏览器缓存后重新加载

### 3. 检查浏览器控制台
打开浏览器开发者工具（F12），检查：

#### Console 标签
- 是否有 JavaScript 错误
- 是否有网络请求错误
- 是否有 React Query 相关错误

#### Network 标签
1. 刷新页面
2. 查找 `/api/data/programs` 请求
3. 检查：
   - **状态码**：应该是 200
   - **请求URL**：应该是 `http://localhost:8000/api/data/programs?page=1&page_size=20`
   - **响应数据**：应该包含 `items`、`total`、`page`、`pageSize` 字段

### 4. 如果仍然不显示数据

#### 检查 React Query 状态
在浏览器控制台执行：
```javascript
// 检查 React Query 缓存
window.__REACT_QUERY_STATE__ = true;
```

#### 手动测试 API
在浏览器控制台执行：
```javascript
fetch('http://localhost:8000/api/data/programs?page=1&page_size=5')
  .then(r => r.json())
  .then(data => console.log('API Response:', data))
  .catch(err => console.error('API Error:', err));
```

#### 检查字段映射
后端返回的字段名（驼峰命名）：
- `programCode`
- `id`
- `title`
- `subTitle`
- `episodeCount`
- `releaseDate`
- `contentInformation`
- `title_en_shortener`
- `seasonId`

前端类型定义应该匹配这些字段名。

## 常见问题

### 问题1: 环境变量未生效
**原因**：Next.js 的环境变量在构建时注入，需要重启服务
**解决**：重启前端开发服务器

### 问题2: CORS 错误
**症状**：浏览器控制台显示 CORS 相关错误
**解决**：检查后端 CORS 配置（已确认配置正确）

### 问题3: 数据格式不匹配
**症状**：API 返回数据但前端无法解析
**解决**：检查 `frontend/src/types/api.ts` 中的类型定义

### 问题4: React Query 缓存问题
**症状**：数据加载一次后不再更新
**解决**：清除浏览器缓存或硬刷新页面

## 验证步骤

1. ✅ 后端服务运行正常
2. ✅ 前端服务运行正常
3. ✅ API 返回数据正常
4. ✅ CORS 配置正确
5. ✅ 环境变量文件已创建
6. ⏳ **需要重启前端服务**
7. ⏳ **需要清除浏览器缓存**

## 联系信息
如果问题仍然存在，请提供：
1. 浏览器控制台的完整错误信息
2. Network 标签中 `/api/data/programs` 请求的详细信息
3. React Query 的查询状态

