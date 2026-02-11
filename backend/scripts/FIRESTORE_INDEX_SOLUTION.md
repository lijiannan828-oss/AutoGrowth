# Firestore 索引解决方案

## 问题回顾

**当前问题**：
- `_find_latest_ready_job` 函数使用 `order_by("updated_at")` + `where("drama_name")` 查询
- 需要 Firestore 复合索引，但索引不存在
- 查询失败，返回 `None, None`

## 解决方案对比

### 方案 A：添加 Firestore 索引（推荐用于大数据量）

**优点**：
- ✅ **性能更好**：Firestore 在数据库层面排序，比内存排序快
- ✅ **可扩展**：即使有数千个 jobs，查询仍然高效
- ✅ **代码简洁**：可以使用 `order_by`，代码更清晰

**缺点**：
- ⚠️ **需要创建索引**：需要手动创建或等待自动创建
- ⚠️ **存储成本**：索引占用存储空间（通常很小）
- ⚠️ **索引构建时间**：首次创建可能需要几分钟

### 方案 B：内存排序（当前实现，推荐用于小数据量）

**优点**：
- ✅ **无需索引**：立即可用，不需要等待索引创建
- ✅ **零配置**：不需要任何额外设置
- ✅ **适合小数据量**：对于每个 drama 只有少量 jobs 的场景，性能足够

**缺点**：
- ⚠️ **性能限制**：如果某个 drama 有数百个 jobs，内存排序可能较慢
- ⚠️ **需要获取更多数据**：需要获取所有符合条件的 jobs 到内存

## 索引创建方法

### 方法 1：通过错误消息自动创建（推荐）

当查询失败时，Firestore 会返回一个链接，可以直接创建索引：

```
FailedPrecondition: 400 The query requires an index. 
You can create it here: 
https://console.firebase.google.com/v1/r/project/.../firestore/indexes?create_composite=...
```

**步骤**：
1. 复制错误消息中的链接
2. 在浏览器中打开
3. 点击"创建索引"
4. 等待索引构建完成（通常几分钟）

### 方法 2：手动在 Firebase Console 创建

**步骤**：
1. 打开 Firebase Console: https://console.firebase.google.com
2. 选择项目：`fleet-blend-469520-n7`
3. 进入 Firestore → Indexes
4. 点击"创建索引"
5. 配置：
   - **Collection ID**: `pipeline_jobs`
   - **Fields**:
     - `drama_name` (Ascending)
     - `updated_at` (Descending)
   - **Query scope**: Collection
6. 点击"创建"
7. 等待索引状态变为"Enabled"（通常几分钟）

### 方法 3：使用 Firebase CLI

```bash
# 创建 firestore.indexes.json 文件
cat > firestore.indexes.json << 'EOF'
{
  "indexes": [
    {
      "collectionGroup": "pipeline_jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "drama_name",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "updated_at",
          "order": "DESCENDING"
        }
      ]
    }
  ]
}
EOF

# 部署索引
firebase deploy --only firestore:indexes
```

## 代码修改（如果使用索引）

如果添加了索引，可以恢复使用 `order_by` 查询：

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

## 推荐方案

### 当前场景分析

**数据量评估**：
- 每个 drama 通常只有 **1-5 个传输任务**
- 即使有多个任务，也很少超过 20 个
- 内存排序的性能完全足够

**推荐**：
- ✅ **保持当前方案（内存排序）**：简单、无需配置、性能足够
- 💡 **如果未来数据量增长**：再考虑添加索引

### 何时应该使用索引

**使用索引的场景**：
- 每个 drama 有 **50+ 个 jobs**
- 需要频繁查询最新 job
- 对查询性能有严格要求

**使用内存排序的场景**：
- 每个 drama 有 **< 20 个 jobs**（当前场景）
- 希望快速部署，无需等待索引创建
- 希望减少配置复杂度

## 索引创建步骤（如果决定使用）

### Step 1: 获取索引创建链接

运行一个会触发索引错误的查询：

```python
from google.cloud import firestore

firestore_client = firestore.Client()
query = (
    firestore_client.collection("pipeline_jobs")
    .where("drama_name", "==", "TEST_DRAMA")
    .order_by("updated_at", direction=firestore.Query.DESCENDING)
    .limit(1)
)

try:
    list(query.stream())
except Exception as e:
    if "index" in str(e).lower():
        # 提取索引创建链接
        import re
        match = re.search(r'https://console\.firebase\.google\.com[^\s]+', str(e))
        if match:
            print(f"索引创建链接: {match.group()}")
```

### Step 2: 创建索引

1. 打开链接或手动创建（见上面的方法）
2. 等待索引状态变为 "Enabled"

### Step 3: 恢复代码

如果使用索引，可以恢复使用 `order_by` 查询（见上面的代码示例）。

## 总结

**问题**：添加索引能解决问题吗？
- ✅ **能**：添加索引后，可以使用 `order_by` 查询

**建议**：
- ✅ **当前场景**：保持内存排序方案（简单、无需配置）
- 💡 **未来优化**：如果数据量增长，再添加索引

**索引创建**：
- 可以通过错误消息链接自动创建
- 或手动在 Firebase Console 创建
- 通常需要几分钟构建时间


