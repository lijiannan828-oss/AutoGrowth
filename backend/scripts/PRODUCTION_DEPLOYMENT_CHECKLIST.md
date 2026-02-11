# 生产环境部署验证清单

## 部署信息

**部署时间**: 2025-11-22  
**提交**: `feat: Switch to database-level sorting with fallback mechanism`  
**主要变更**:
- ✅ 切换到数据库层面排序（`order_by`）
- ✅ 添加内存排序回退机制
- ✅ 部署 Firestore 复合索引

## 验证步骤

### Step 1: 检查 CI/CD 部署状态

**GitHub Actions**:
```
https://github.com/lijiannan828-oss/AutoGrowth/actions
```

**验证点**:
- [ ] CI/CD 工作流已启动
- [ ] 构建成功
- [ ] Relay Service 部署成功
- [ ] 所有 Jobs 部署成功

### Step 2: 检查 Relay Service 状态

```bash
gcloud run services describe drama-processor-relay-service \
  --region us-central1 \
  --project fleet-blend-469520-n7 \
  --format="value(status.url)"
```

**验证点**:
- [ ] Service 状态为 "Ready"
- [ ] URL 可访问
- [ ] 最新 revision 已部署

### Step 3: 检查 Firestore 索引状态

**Firebase Console**:
```
https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore/indexes
```

**验证点**:
- [ ] 索引状态为 "Enabled"（或 "Building"）
- [ ] `drama_name` + `updated_at` 索引存在

### Step 4: 测试自动触发功能

**测试 Drama**: `KR071P01S01_타임 리프 조선`

**方法 1: 使用验证脚本**
```bash
./backend/scripts/verify_production_deployment.sh
```

**方法 2: 手动测试**
```bash
# 1. 检查传输任务是否存在
python3 backend/scripts/test_find_ready_job.py

# 2. 测试 Relay Service 端点
curl -X POST "https://drama-processor-relay-service-<hash>.a.run.app/api/relay/event" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "google.cloud.storage.object.v1.finalized",
    "data": {
      "bucket": "vigloo_source",
      "name": "KR071P01S01_타임 리프 조선/_PROCESS_NOW.txt"
    }
  }'
```

**验证点**:
- [ ] Relay Service 返回 `{"status": "triggered"}`
- [ ] 处理任务被创建
- [ ] 日志显示使用数据库排序（如果索引已启用）

### Step 5: 检查日志

**Relay Service 日志**:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=drama-processor-relay-service" \
  --limit 50 \
  --format="table(timestamp,textPayload)" \
  --project fleet-blend-469520-n7
```

**验证点**:
- [ ] 日志显示 "✅ 找到 ready job (数据库排序)" 或 "⚠️ 索引正在构建中，使用内存排序回退方案"
- [ ] 没有错误日志
- [ ] 查询成功

### Step 6: 端到端测试（可选）

**创建新的传输任务**:
1. 通过前端或 API 创建一个新的传输任务
2. 等待传输完成
3. 观察是否自动触发压制任务

**验证点**:
- [ ] 传输任务完成后自动创建 `_PROCESS_NOW.txt`
- [ ] Eventarc 捕获事件
- [ ] Relay Service 接收请求
- [ ] 处理任务被正确触发

## 预期结果

### 索引已启用时
- ✅ 日志显示 "✅ 找到 ready job (数据库排序)"
- ✅ 查询性能更好
- ✅ 自动触发功能正常

### 索引构建中时
- ⏳ 日志显示 "⚠️ 索引正在构建中，使用内存排序回退方案"
- ✅ 功能仍然正常（使用内存排序）
- ✅ 索引构建完成后自动切换

## 故障排除

### 问题 1: Relay Service 返回 "job_not_found"

**可能原因**:
- 索引还未构建完成
- 查询条件不匹配
- Firestore 中没有 ready job

**解决方法**:
1. 检查索引状态
2. 检查 Firestore 中是否有传输完成的任务
3. 查看日志了解详细信息

### 问题 2: 查询失败

**可能原因**:
- 索引配置错误
- 查询语法错误

**解决方法**:
1. 检查索引配置
2. 查看错误日志
3. 验证查询条件

### 问题 3: 自动触发不工作

**可能原因**:
- Eventarc 触发器配置问题
- Relay Service 未正确部署
- 信号文件未创建

**解决方法**:
1. 检查 Eventarc 触发器配置
2. 检查 Relay Service 状态
3. 检查 GCS 中是否有 `_PROCESS_NOW.txt` 文件

## 相关链接

- **GitHub Actions**: https://github.com/lijiannan828-oss/AutoGrowth/actions
- **Firebase Console**: https://console.firebase.google.com/project/fleet-blend-469520-n7
- **Cloud Run**: https://console.cloud.google.com/run?project=fleet-blend-469520-n7
- **Firestore Indexes**: https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore/indexes


