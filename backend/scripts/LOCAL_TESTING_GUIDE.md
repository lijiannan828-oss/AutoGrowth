# 本地测试指南

## 问题：如何解除测试限制？

### 限制 1: 本地环境没有安装 google-cloud-run 依赖

**解决方案**:
```bash
# 激活虚拟环境
cd backend
source venv/bin/activate

# 安装依赖
pip install google-cloud-run

# 或者安装所有依赖
pip install -r requirements.txt
```

**自动化脚本**:
```bash
./backend/scripts/setup_local_test_env.sh
```

### 限制 2: 需要 GCP 认证才能实际调用 API

**解决方案 1: 使用服务账号密钥文件**
```bash
# 设置环境变量
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 或者使用项目中的密钥（如果存在）
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/backend/secrets/sa-run-prod-key.json
```

**解决方案 2: 使用 gcloud 默认认证**
```bash
gcloud auth application-default login
```

**解决方案 3: 使用 Mock 测试（不需要认证）**
```bash
python -m backend.scripts.test_with_mock
```

### 限制 3: 无法完全模拟生产环境

**解决方案 1: 使用 Mock 进行单元测试**
- ✅ 不需要 GCP 认证
- ✅ 可以模拟各种场景
- ✅ 运行快速
- ⚠️  不完全等同于真实环境

**解决方案 2: 使用真实 GCP 环境进行集成测试**
- ✅ 完全等同于生产环境
- ✅ 可以验证真实 API 调用
- ⚠️  需要 GCP 认证
- ⚠️  可能产生费用

## 测试方法

### 方法 1: Mock 测试（推荐用于开发）

```bash
# 运行 Mock 测试（不需要 GCP 认证）
python -m backend.scripts.test_with_mock
```

**优点**:
- ✅ 不需要 GCP 认证
- ✅ 运行快速
- ✅ 可以测试各种场景
- ✅ 不会产生费用

**缺点**:
- ⚠️  不完全等同于真实环境
- ⚠️  可能遗漏真实 API 的问题

### 方法 2: 真实 API 测试（推荐用于验证）

```bash
# 1. 设置认证
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
# 或者
gcloud auth application-default login

# 2. 运行真实 API 测试
python -m backend.scripts.test_concurrency_service_local [job_id]
```

**优点**:
- ✅ 完全等同于生产环境
- ✅ 可以验证真实 API 调用
- ✅ 可以发现真实问题

**缺点**:
- ⚠️  需要 GCP 认证
- ⚠️  可能产生少量费用
- ⚠️  运行较慢

### 方法 3: 混合测试（推荐）

1. **开发阶段**: 使用 Mock 测试快速迭代
2. **验证阶段**: 使用真实 API 测试验证
3. **部署前**: 再次使用真实 API 测试确认

## 快速开始

### 1. 设置环境

```bash
# 运行环境设置脚本
./backend/scripts/setup_local_test_env.sh
```

### 2. 运行 Mock 测试（不需要认证）

```bash
python -m backend.scripts.test_with_mock
```

### 3. 运行真实 API 测试（需要认证）

```bash
# 设置认证
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 运行测试
python -m backend.scripts.test_concurrency_service_local NU3xvcuvxzutenLi5BNX
```

## 测试脚本说明

### test_with_mock.py
- **用途**: Mock 测试，不需要 GCP 认证
- **测试内容**: 
  - 取消状态检测
  - 成功状态检测
  - 运行中状态检测
- **运行**: `python -m backend.scripts.test_with_mock`

### test_concurrency_service_local.py
- **用途**: 真实 API 测试，需要 GCP 认证
- **测试内容**: 
  - 检查指定 Job ID 的执行状态
  - 测试清理逻辑（可选）
- **运行**: `python -m backend.scripts.test_concurrency_service_local [job_id] [--cleanup]`

## 故障排除

### 问题 1: ModuleNotFoundError: No module named 'google.cloud.run_v2'

**解决方案**:
```bash
pip install google-cloud-run
```

### 问题 2: FailedPrecondition: 400 The request requires authentication

**解决方案**:
```bash
# 设置认证
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
# 或者
gcloud auth application-default login
```

### 问题 3: Permission denied

**解决方案**:
- 确保服务账号有足够的权限
- 检查服务账号是否有 `roles/run.viewer` 或 `roles/run.admin` 角色

## 总结

✅ **现在可以解除所有限制**:
1. ✅ 安装 `google-cloud-run` 依赖
2. ✅ 设置 GCP 认证（或使用 Mock 测试）
3. ✅ 使用 Mock 测试模拟生产环境

📝 **推荐工作流程**:
1. 开发时使用 Mock 测试快速迭代
2. 验证时使用真实 API 测试
3. 部署前再次使用真实 API 测试确认
