# 大规模下载功能升级方案

## 一、当前实现分析

### ✅ 可行的部分

1. **File System Access API 使用**
   - ✅ 使用 `showDirectoryPicker` 获取目录权限
   - ✅ 使用 `pipeTo` 进行流式下载，避免内存溢出
   - ✅ 使用 `FileSystemWritableFileStream` 直接写入本地文件系统

2. **并发下载机制**
   - ✅ 实现了基本的并发下载队列
   - ✅ 使用 Promise.all 管理并发任务

3. **进度跟踪**
   - ✅ 实时更新下载进度
   - ✅ 显示下载速度和预计时间

4. **错误处理**
   - ✅ 单个文件失败不影响整体下载
   - ✅ 记录失败文件详情

### ❌ 不足的部分

1. **内存管理**
   - ❌ 一次性获取所有文件的签名 URL（5000-6000个文件）
   - ❌ 前端维护所有文件状态在内存中
   - ❌ 没有分批处理机制

2. **并发控制**
   - ❌ 固定并发数5，过于保守
   - ❌ 没有动态调整并发数
   - ❌ 没有考虑浏览器资源限制（内存、连接数）

3. **网络请求**
   - ❌ 一次性获取所有签名 URL，可能导致请求超时
   - ❌ 没有重试机制
   - ❌ 没有网络错误恢复机制

4. **持久化与恢复**
   - ❌ 没有进度持久化（IndexedDB）
   - ❌ 没有断点续传机制
   - ❌ 浏览器刷新后无法恢复下载

5. **用户体验**
   - ❌ 无法暂停/恢复下载
   - ❌ 没有下载队列管理
   - ❌ 大量文件时浏览器可能崩溃

## 二、升级方案

### 方案 1: 分批获取签名 URL（短期优化）

**目标**: 解决一次性获取所有签名 URL 的内存和超时问题

**实现**:
1. 后端 `/batch-urls` 支持分页参数：
   - `limit`: 每批返回的文件数（默认1000）
   - `offset`: 偏移量
   - `total_count`: 总文件数（首次请求返回）

2. 前端分批请求：
   - 首次请求获取总文件数
   - 按批次（1000个/批）获取签名 URL
   - 每批下载完成后再获取下一批

**优点**:
- 实现简单，改动小
- 立即解决内存和超时问题
- 不需要大规模重构

**缺点**:
- 仍然需要维护所有文件状态
- 无法解决浏览器长时间运行崩溃问题

### 方案 2: 动态并发控制（中期优化）

**目标**: 提高下载效率，同时避免浏览器资源耗尽

**实现**:
1. 动态并发数调整：
   - 初始并发数：`Math.min(10, Math.ceil(totalFiles / 100))`
   - 根据下载速度动态调整：
     - 如果平均速度 > 阈值，增加并发数（最多20）
     - 如果平均速度 < 阈值，减少并发数（最少3）
   - 根据浏览器性能调整：
     - 检测可用内存（`navigator.deviceMemory`）
     - 检测 CPU 使用率（通过 Web Workers）

2. 智能队列管理：
   - 优先下载小文件（快速完成，提升用户体验）
   - 大文件使用较低的并发数
   - 失败文件自动重试（最多3次）

**优点**:
- 显著提高下载效率
- 避免浏览器资源耗尽
- 更好的用户体验

**缺点**:
- 需要实现性能监控
- 逻辑复杂度增加

### 方案 3: IndexedDB 持久化 + 断点续传（长期优化）

**目标**: 支持暂停/恢复，浏览器刷新后继续下载

**实现**:
1. IndexedDB 存储：
   - 下载任务元数据（taskId, paths, totalFiles, etc.）
   - 每个文件的下载状态（pending, downloading, completed, failed）
   - 已下载文件的字节数（用于断点续传）

2. 断点续传：
   - 下载前检查文件是否已存在
   - 如果存在，检查文件大小是否匹配
   - 支持 Range 请求（`Range: bytes=start-end`）
   - 后端 `/download-proxy` 支持 Range 头

3. 恢复机制：
   - 页面加载时检查 IndexedDB 中的未完成任务
   - 自动恢复下载
   - 用户可以选择继续或取消

**优点**:
- 完全解决浏览器崩溃问题
- 支持暂停/恢复
- 更好的用户体验

**缺点**:
- 实现复杂度高
- 需要后端支持 Range 请求
- IndexedDB 存储可能较大

### 方案 4: Service Worker + 后台下载（终极方案）

**目标**: 完全后台下载，不依赖浏览器标签页

**实现**:
1. Service Worker 注册：
   - 注册 Service Worker 处理下载任务
   - 使用 Background Sync API 确保下载完成

2. 后台下载：
   - 下载任务在 Service Worker 中执行
   - 不依赖浏览器标签页
   - 支持浏览器关闭后继续下载

3. 通知机制：
   - 使用 Web Notifications API
   - 下载完成/失败时通知用户

**优点**:
- 完全后台下载
- 不依赖浏览器标签页
- 最佳用户体验

**缺点**:
- 实现复杂度极高
- Service Worker 有生命周期限制
- 需要处理各种边界情况

## 三、推荐实施路径

### 阶段 1: 立即实施（1-2天）
**方案 1: 分批获取签名 URL**
- 后端支持分页参数
- 前端分批请求和下载
- **预期效果**: 解决内存和超时问题，支持5000-6000个文件下载

### 阶段 2: 短期优化（3-5天）
**方案 2: 动态并发控制**
- 实现动态并发数调整
- 智能队列管理
- **预期效果**: 下载效率提升2-3倍，避免浏览器资源耗尽

### 阶段 3: 中期优化（1-2周）
**方案 3: IndexedDB 持久化 + 断点续传**
- 实现进度持久化
- 支持断点续传
- **预期效果**: 支持暂停/恢复，浏览器刷新后继续下载

### 阶段 4: 长期优化（可选）
**方案 4: Service Worker + 后台下载**
- 实现完全后台下载
- **预期效果**: 最佳用户体验，但实现复杂度高

## 四、技术细节

### 1. 分批获取签名 URL

**后端 API 变更**:
```python
@router.post("/batch-urls")
def batch_download_urls(
    request: BatchDownloadUrlsRequest,
    limit: int = Query(1000, description="每批返回的文件数"),
    offset: int = Query(0, description="偏移量"),
):
    # 返回: { files: [...], total_count: int, has_more: bool }
```

**前端实现**:
```typescript
async function fetchBatchUrlsInChunks(paths: string[], chunkSize: number = 1000) {
  const chunks: BatchDownloadItem[][] = [];
  for (let i = 0; i < paths.length; i += chunkSize) {
    const chunk = await fetchBatchDownloadUrls(paths.slice(i, i + chunkSize));
    chunks.push(chunk.files);
  }
  return chunks.flat();
}
```

### 2. 动态并发控制

**实现**:
```typescript
class DynamicConcurrencyController {
  private currentConcurrency: number;
  private minConcurrency = 3;
  private maxConcurrency = 20;
  
  adjustConcurrency(avgSpeed: number, targetSpeed: number) {
    if (avgSpeed > targetSpeed * 1.2) {
      this.currentConcurrency = Math.min(
        this.maxConcurrency,
        this.currentConcurrency + 2
      );
    } else if (avgSpeed < targetSpeed * 0.8) {
      this.currentConcurrency = Math.max(
        this.minConcurrency,
        this.currentConcurrency - 1
      );
    }
  }
}
```

### 3. IndexedDB 持久化

**数据结构**:
```typescript
interface DownloadTask {
  taskId: string;
  paths: string[];
  totalFiles: number;
  completedFiles: number;
  failedFiles: number;
  status: 'pending' | 'downloading' | 'paused' | 'completed' | 'failed';
  createdAt: number;
  updatedAt: number;
}

interface FileDownloadState {
  taskId: string;
  path: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  downloadedBytes: number;
  totalBytes: number;
}
```

### 4. 断点续传

**Range 请求支持**:
```typescript
async function downloadFileWithResume(
  file: BatchDownloadItem,
  existingSize: number
): Promise<Response> {
  const headers: HeadersInit = {};
  if (existingSize > 0) {
    headers['Range'] = `bytes=${existingSize}-`;
  }
  return fetch(proxyUrl, { headers });
}
```

## 五、风险评估

### 方案 1 风险
- **低风险**: 实现简单，改动小
- **建议**: 立即实施

### 方案 2 风险
- **中风险**: 需要性能监控，可能影响现有功能
- **建议**: 充分测试后实施

### 方案 3 风险
- **中高风险**: IndexedDB 存储可能较大，需要清理机制
- **建议**: 分阶段实施，先实现持久化，再实现断点续传

### 方案 4 风险
- **高风险**: 实现复杂度高，Service Worker 有生命周期限制
- **建议**: 仅在必要时实施

## 六、性能指标

### 当前性能（5000个文件）
- 下载时间: ~2-3小时（假设每个文件10MB，5并发）
- 内存占用: ~500MB（所有文件状态）
- 浏览器稳定性: 可能崩溃

### 方案 1 后（5000个文件）
- 下载时间: ~2-3小时（不变）
- 内存占用: ~100MB（分批处理）
- 浏览器稳定性: 显著改善

### 方案 2 后（5000个文件）
- 下载时间: ~1-1.5小时（并发数提升）
- 内存占用: ~100MB
- 浏览器稳定性: 良好

### 方案 3 后（5000个文件）
- 下载时间: ~1-1.5小时
- 内存占用: ~100MB
- 浏览器稳定性: 优秀（支持恢复）
- 用户体验: 优秀（支持暂停/恢复）

## 七、实施建议

1. **立即实施方案 1**: 解决当前最紧迫的内存和超时问题
2. **1周内实施方案 2**: 提升下载效率
3. **2周内实施方案 3**: 完善用户体验
4. **根据需求考虑方案 4**: 仅在必要时实施


