# 第四阶段：生产环境部署检查清单

## 部署状态

### ✅ 代码已提交并推送
- **Commit**: Sharding architecture implementation
- **Branch**: main
- **Trigger**: Push to main branch (自动触发 CI/CD)

## CI/CD 部署流程

### Step 1: GitHub Actions 工作流
- **工作流名称**: Backend Deploy to Cloud Run
- **触发方式**: Push to main branch
- **GitHub Actions URL**: https://github.com/lijiannan828-oss/AutoGrowth/actions

### Step 2: 部署组件

#### 1. Docker 镜像构建
- **Registry**: `us-central1-docker.pkg.dev/fleet-blend-469520-n7/autogrowth-docker/autogrowth-backend`
- **Tag**: `{GITHUB_SHA}`

#### 2. Cloud Run Jobs 部署

**drama-processor-job** (关键更新):
- **CPU**: 2 (从 8 降低)
- **Memory**: 4Gi (从 32Gi 降低)
- **Parallelism**: 50 (从 5 增加)
- **Task Timeout**: 7200s (2h，从 24h 降低)

**其他 Jobs**:
- `gdrive-transfer-worker`: 保持不变
- `zip-compress-worker`: 保持不变

#### 3. Cloud Run Services 部署

**drama-processor-relay-service**:
- 已更新以支持 Sharding（计算 task_count）

**autogrowth-backend**:
- 主 API 服务

## 部署后验证步骤

### 1. 检查 GitHub Actions 部署状态

访问：https://github.com/lijiannan828-oss/AutoGrowth/actions

**验证点**：
- ✅ 工作流运行成功（绿色 ✓）
- ✅ 所有部署步骤完成
- ✅ 健康检查通过

### 2. 验证 Cloud Run Job 配置

```bash
gcloud run jobs describe drama-processor-job \
  --region us-central1 \
  --project fleet-blend-469520-n7 \
  --format="yaml(spec.template.spec.containers[0].resources,spec.parallelism,spec.template.spec.timeoutSeconds)"
```

**预期输出**：
- `cpu`: "2"
- `memory`: "4Gi"
- `parallelism`: 50
- `timeoutSeconds`: 7200

### 3. 验证 Relay Service 配置

```bash
gcloud run services describe drama-processor-relay-service \
  --region us-central1 \
  --project fleet-blend-469520-n7 \
  --format="value(status.url)"
```

**验证点**：
- ✅ Service URL 可访问
- ✅ `/api/relay/event` 端点正常响应

### 4. 生产环境测试

#### 测试场景 1: 小规模测试（< 100 文件）

1. **准备测试数据**：
   - 上传一个包含 10-20 个文件的剧集到 GDrive
   - 触发传输任务
   - 等待传输完成

2. **观察 Relay Service**：
   - 检查 Relay Service 日志
   - 确认 `task_count` 计算正确（应该等于文件数）

3. **观察 Cloud Run Jobs**：
   - 访问 Cloud Run Jobs 控制台
   - 确认启动了正确数量的 Tasks
   - 确认每个 Task 处理不同的文件

4. **验证 Firestore**：
   - 检查主文档 `total_files`, `processed_files`, `failed_files`
   - 检查 Task 文档（`tasks/0`, `tasks/1`, ...）
   - 确认状态最终变为 `SUCCEEDED`

#### 测试场景 2: 大规模测试（> 100 文件）

1. **准备测试数据**：
   - 上传一个包含 200+ 个文件的剧集
   - 触发传输任务

2. **观察关键指标**：
   - **task_count**: 应该被限制为 100（即使文件数 > 100）
   - **Task 数量**: Cloud Run Jobs 应该启动 100 个 Tasks
   - **每个 Task 处理**: 每个 Task 处理 2-3 个文件（200/100）

3. **验证无 OOM**：
   - 监控 Cloud Run Jobs 日志
   - 确认没有 `exit=-9` (SIGKILL/OOM) 错误
   - 确认所有 Tasks 正常完成

### 5. 监控和观察

#### Cloud Run Jobs 控制台
```
https://console.cloud.google.com/run/jobs/us-central1/drama-processor-job/executions
```

**关键观察点**：
- ✅ Execution 状态：SUCCEEDED
- ✅ Task 数量：符合预期（task_count）
- ✅ 无失败 Tasks
- ✅ 执行时间：合理（< 2h）

#### Firestore 控制台
```
https://console.cloud.google.com/firestore/databases/-default-/data/~2Fpipeline_jobs
```

**关键观察点**：
- ✅ 主文档 `total_files` 正确设置
- ✅ `processed_files` 和 `failed_files` 正确更新
- ✅ Task 文档正确创建和更新
- ✅ 最终状态为 `SUCCEEDED`

#### Cloud Logging
```
https://console.cloud.google.com/logs/query
```

**查询示例**：
```
resource.type="cloud_run_job"
resource.labels.job_name="drama-processor-job"
severity>=ERROR
```

**关键观察点**：
- ✅ 无 OOM 错误（`exit=-9`）
- ✅ 无 Firestore 写入冲突
- ✅ 分片逻辑正确（日志显示不同 Task 处理不同文件）

## 回滚计划

如果生产环境验证失败：

### 立即行动
1. **停止正在运行的 Job Execution**：
   ```bash
   gcloud run jobs executions cancel <EXECUTION_NAME> \
     --region us-central1 \
     --project fleet-blend-469520-n7
   ```

2. **回滚代码**：
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **等待重新部署完成**

### 手动恢复（如需要）
- 使用旧版逻辑手动触发剩余文件的处理
- 可能需要临时脚本处理部分完成的 Job

## 成功标准

✅ **所有以下条件必须满足**：

1. ✅ GitHub Actions 部署成功
2. ✅ Cloud Run Job 配置正确（CPU=2, Memory=4Gi, Parallelism=50）
3. ✅ Relay Service 正确计算 `task_count`
4. ✅ 小规模测试（< 100 文件）通过
5. ✅ 大规模测试（> 100 文件）通过，无 OOM
6. ✅ Firestore 状态追踪正确
7. ✅ 所有 Tasks 正常完成，无失败

## 部署时间线

- **代码推送时间**: [待填写]
- **CI/CD 开始时间**: [待填写]
- **部署完成时间**: [待填写]
- **测试开始时间**: [待填写]
- **测试完成时间**: [待填写]

---

**部署完成后，请按照上述步骤进行验证。**


