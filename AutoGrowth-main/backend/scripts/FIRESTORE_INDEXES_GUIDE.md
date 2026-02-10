# Firestore 索引创建指南

## 概述

本文档说明如何为常用字段创建 Firestore 复合索引，以优化查询性能。

## 索引配置

索引配置已保存在 `firestore.indexes.json` 文件中，包含以下索引：

### 1. pipeline_jobs 集合索引

#### 索引 1: drama_name + updated_at
- **用途**: `_find_latest_ready_job` 函数
- **查询模式**: `where("drama_name") + order_by("updated_at")`
- **字段**: 
  - `drama_name` (ASCENDING)
  - `updated_at` (DESCENDING)

#### 索引 2: status + updated_at
- **用途**: 按状态查询最新任务
- **查询模式**: `where("status") + order_by("updated_at")`
- **字段**:
  - `status` (ASCENDING)
  - `updated_at` (DESCENDING)

#### 索引 3: stage + updated_at
- **用途**: 按阶段查询最新任务
- **查询模式**: `where("stage") + order_by("updated_at")`
- **字段**:
  - `stage` (ASCENDING)
  - `updated_at` (DESCENDING)

#### 索引 4: drama_name + status + updated_at
- **用途**: 按 drama 和状态查询最新任务
- **查询模式**: `where("drama_name") + where("status") + order_by("updated_at")`
- **字段**:
  - `drama_name` (ASCENDING)
  - `status` (ASCENDING)
  - `updated_at` (DESCENDING)

#### 索引 5: drama_name + stage + updated_at
- **用途**: 按 drama 和阶段查询最新任务
- **查询模式**: `where("drama_name") + where("stage") + order_by("updated_at")`
- **字段**:
  - `drama_name` (ASCENDING)
  - `stage` (ASCENDING)
  - `updated_at` (DESCENDING)

#### 索引 6: transfer_completed + updated_at
- **用途**: 查询传输完成的任务
- **查询模式**: `where("transfer_completed") + order_by("updated_at")`
- **字段**:
  - `transfer_completed` (ASCENDING)
  - `updated_at` (DESCENDING)

#### 索引 7: drama_name + transfer_completed + updated_at
- **用途**: 查询特定 drama 的传输完成任务
- **查询模式**: `where("drama_name") + where("transfer_completed") + order_by("updated_at")`
- **字段**:
  - `drama_name` (ASCENDING)
  - `transfer_completed` (ASCENDING)
  - `updated_at` (DESCENDING)

### 2. google_oauth_tokens 集合索引

#### 索引 8: userId + updatedAt
- **用途**: 查找用户的最新 token
- **查询模式**: `where("userId") + order_by("updatedAt")`
- **字段**:
  - `userId` (ASCENDING)
  - `updatedAt` (DESCENDING)

#### 索引 9: userEmail + updatedAt
- **用途**: 查找用户邮箱的最新 token
- **查询模式**: `where("userEmail") + order_by("updatedAt")`
- **字段**:
  - `userEmail` (ASCENDING)
  - `updatedAt` (DESCENDING)

## 创建索引的方法

### 方法 1: 使用脚本（推荐）

```bash
# 运行创建脚本
./backend/scripts/create_firestore_indexes.sh
```

脚本会：
1. 检查依赖（gcloud CLI）
2. 显示索引配置预览
3. 使用 Firebase CLI 部署索引（如果可用）
4. 或提供手动创建指南

### 方法 2: 使用 Firebase CLI

```bash
# 安装 Firebase CLI（如果未安装）
npm install -g firebase-tools

# 登录 Firebase
firebase login

# 部署索引
firebase deploy --only firestore:indexes --project fleet-blend-469520-n7
```

### 方法 3: 手动在 Firebase Console 创建

1. 打开 Firebase Console:
   https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore/indexes

2. 点击 "创建索引"

3. 按照 `firestore.indexes.json` 中的配置创建每个索引

4. 等待索引状态变为 "Enabled"（通常需要几分钟）

### 方法 4: 通过错误消息自动创建

当查询失败时，Firestore 会返回一个链接，可以直接创建索引：

1. 运行一个会触发索引错误的查询
2. 复制错误消息中的链接
3. 在浏览器中打开
4. 点击 "创建索引"

## 验证索引状态

### 在 Firebase Console 查看

1. 打开: https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore/indexes
2. 查看索引状态:
   - **Building**: 正在构建
   - **Enabled**: 已启用，可以使用
   - **Error**: 构建失败

### 使用 gcloud CLI 查看

```bash
gcloud firestore indexes list --project=fleet-blend-469520-n7
```

## 索引构建时间

- **小型索引**: 1-2 分钟
- **中型索引**: 3-5 分钟
- **大型索引**: 5-10 分钟

索引构建完成后，状态会变为 "Enabled"，即可使用。

## 代码修改

创建索引后，可以恢复使用 `order_by` 查询：

### 修改 `_find_latest_ready_job` 函数

```python
def _find_latest_ready_job(drama_name: str) -> Tuple[str, Dict[str, Any]] | Tuple[None, None]:
    """Find the latest ready job for a given drama_name.
    
    Requires Firestore composite index:
    - Collection: pipeline_jobs
    - Fields: drama_name (Ascending), updated_at (Descending)
    """
    firestore_client = _get_firestore_client()
    
    # Query with order_by (requires composite index)
    query = (
        firestore_client.collection(FIRESTORE_COLLECTION)
        .where("drama_name", "==", drama_name)
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .limit(20)
    )
    
    try:
        for snapshot in query.stream():
            data = snapshot.to_dict() or {}
            if not data:
                continue
            transfer_completed = bool(data.get("transfer_completed"))
            stage = data.get("stage")
            if transfer_completed and (stage == 1 or stage is None):
                logger.info(
                    "✅ 找到 ready job: %s (drama=%s, updated_at=%s)",
                    snapshot.id,
                    drama_name,
                    data.get("updated_at"),
                )
                return snapshot.id, data
        
        logger.warning("⚠️  未找到 ready job (drama=%s)", drama_name)
        return None, None
    
    except Exception as exc:
        logger.exception("❌ 查询 ready job 失败 (drama=%s): %s", drama_name, exc)
        return None, None
```

## 注意事项

1. **索引成本**: 索引占用存储空间，但通常很小（每个索引几 KB）
2. **索引维护**: Firestore 自动维护索引，无需手动更新
3. **查询性能**: 使用索引后，查询性能会显著提升
4. **索引限制**: 每个集合最多 200 个复合索引

## 故障排除

### 索引创建失败

如果索引创建失败，检查：
1. 字段名称是否正确
2. 字段类型是否匹配
3. 集合名称是否正确

### 查询仍然失败

如果创建索引后查询仍然失败：
1. 确认索引状态为 "Enabled"
2. 检查查询条件是否与索引匹配
3. 查看错误消息中的索引创建链接

## 相关文件

- `firestore.indexes.json`: 索引配置文件
- `backend/scripts/create_firestore_indexes.sh`: 索引创建脚本
- `backend/app/api/v1/relay.py`: 使用索引的代码


