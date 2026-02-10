# Sharding 重构测试方案文档

## 1. 测试目标
验证 Cloud Run Jobs 的 Sharding（分片）机制在开发环境和生产环境的正确性，确保：
1. **分片逻辑正确**：所有文件被“不重不漏”地分配给各个 Task。
2. **状态追踪准确**：Firestore 中 Task 级的细粒度进度和主文档的汇总进度一致。
3. **并发处理安全**：多个 Worker 同时写入 Firestore 不会产生冲突。
4. **系统鲁棒性**：在部分 Task 失败或重启时，系统能正确处理（断点续传）。

## 2. 环境差异对照表 (Diff Spec)

| 维度 | 开发环境 (Local / Dev) | 生产环境 (Cloud Run Jobs) |
| :--- | :--- | :--- |
| **运行方式** | `subprocess.Popen` / Shell 脚本模拟 | Cloud Run 调度器自动启动 |
| **分片参数** | **手动注入**：`CLOUD_RUN_TASK_INDEX` / `COUNT` | **平台注入**：GCP 自动分配 |
| **凭证认证** | `GOOGLE_APPLICATION_CREDENTIALS` (本地 JSON) | ADC (Metadata Server / Secret Mount) |
| **FFmpeg** | 本地安装 (macOS/Linux) | Docker 镜像预装 |
| **临时目录** | 系统临时目录 (`/var/folders/...`) | 容器内存文件系统 `/tmp` (需严格清理) |
| **并发模拟** | 多进程模拟 (受限于本地 CPU/RAM) | 云端大规模并发 (主要受限于配额) |

## 3. 测试阶段与执行计划

### 第一阶段：单元测试与逻辑验证 (Unit Testing)
**目标**：验证分片算法纯逻辑，不依赖外部 IO。

*   **工具**：`backend/scripts/test_sharding_logic.py`
*   **内容**：
    *   模拟 100 个文件 ID。
    *   设置 `task_count=5`。
    *   循环 `task_index` 从 0 到 4，收集每个 Index “领取”的文件。
    *   **断言**：
        *   所有文件都被领取了 (Sum(claimed) == 100)。
        *   没有文件被重复领取 (Set(all_claimed) size == 100)。
        *   每个 Task 领取数量均匀 (理想情况下各 20 个)。

### 第二阶段：本地集成测试 (Local Integration Testing)
**目标**：在本地模拟真实 Worker 运行，验证 Firestore 交互和 GCS 下载/上传。

*   **工具**：
    *   `backend/scripts/run_process_worker_local.sh`: 模拟器启动脚本。
    *   `backend/scripts/test_relay_local_sharding.py`: 自动化测试脚本 (可选，替代手动操作)。
*   **前置条件**：
    *   GCS `vigloo_source` 中存在测试剧集 (如 `TEST_SHARDING_001`)，含少量文件 (如 4 个视频)。
    *   本地已配置 `GOOGLE_APPLICATION_CREDENTIALS`。
*   **步骤**：
    1.  **手动创建 Job**：在 Firestore `pipeline_jobs` 创建一个状态为 `QUEUED` 的 Job。
    2.  **模拟并发启动**：
        *   终端 1: `./run_process_worker_local.sh <JOB_ID> 0 2` (模拟 Task 0/2)
        *   终端 2: `./run_process_worker_local.sh <JOB_ID> 1 2` (模拟 Task 1/2)
    3.  **验证**：
        *   **日志**：观察两个终端是否分别处理了不同的文件 (例如 Task 0 处理 ep1/3, Task 1 处理 ep2/4)。
        *   **Firestore**：
            *   检查 `tasks/0` 和 `tasks/1` 文档是否存在且状态为 `COMPLETED`。
            *   检查主文档 `processed_files` 是否为 4。
            *   检查主文档 `status` 是否最终变为 `SUCCEEDED`。

### 第三阶段：Relay Service 改造验证
**目标**：验证 Relay Service 能正确计算文件数并触发 Worker (本地模式)。

*   **场景**：Relay 接收到 Eventarc 信号。
*   **验证**：
    *   Relay 日志显示 `Calculated task_count=...`。
    *   Relay 正确调用了本地模拟启动逻辑 (启动了正确数量的子进程)。

### 第四阶段：生产环境验收 (UAT)
**目标**：部署后在大规模真实数据下的表现。

*   **步骤**：
    1.  部署 Relay Service 和 Worker Jobs。
    2.  上传一个真实剧集 (例如 50 集) 到 GDrive 并触发传输。
    3.  观察传输完成后，Relay 是否自动触发压制 Job。
    4.  **关键观察点**：
        *   Cloud Run Jobs 控制台显示启动了 50 个 Tasks (或 min(50, 100))。
        *   查看 Firestore `tasks` 子集合，确认每个 Task 都在更新自己的状态。
        *   确认无 OOM 报错。

## 4. 回滚策略
如果生产环境验证失败：
1.  **立即停止 Job**：在 Cloud Run 控制台停止正在运行的 Execution。
2.  **回滚代码**：Revert Git 提交，重新部署旧版本 Worker 和 Relay。
3.  **手动恢复**：使用旧版逻辑手动触发剩余文件的处理 (可能需要临时脚本)。

---
**请确认本测试方案是否通过？** 确认后将开始执行第一阶段。


