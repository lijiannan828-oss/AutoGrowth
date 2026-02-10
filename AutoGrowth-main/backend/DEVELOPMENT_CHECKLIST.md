# 开发检查清单

## API 调用检查清单

### 📝 代码编写阶段

**当编写包含 GCP API 调用的代码时**：

- [ ] **使用官方客户端库**
  - [ ] 是否使用官方客户端库（如 `run_v2.JobsClient()`）？
  - [ ] 是否禁止使用 REST API 直接调用？
  - [ ] API 调用格式是否正确？

- [ ] **跨文件对比**
  - [ ] 是否有其他文件实现了相同功能？
  - [ ] 实现方式是否一致？
  - [ ] 是否使用相同的 API 客户端？

- [ ] **错误处理**
  - [ ] 是否捕获异常？
  - [ ] 错误消息是否有意义？
  - [ ] 是否记录详细错误信息？

### 🔍 代码审查阶段

**代码审查时检查**：

- [ ] **API 调用检查**
  - [ ] 是否使用官方客户端库？
  - [ ] 是否禁止使用 REST API？
  - [ ] API 调用格式是否正确？

- [ ] **跨文件对比检查**
  - [ ] 是否有其他文件实现了相同功能？
  - [ ] 实现方式是否一致？
  - [ ] 是否使用相同的 API 客户端？

- [ ] **错误处理检查**
  - [ ] 错误处理是否完善？
  - [ ] 错误消息是否有意义？
  - [ ] 是否记录详细错误信息？

## Firestore 查询开发检查清单

### 📝 代码编写阶段

**当编写包含 Firestore 查询的代码时**：

- [ ] **识别查询模式**
  - [ ] 是否使用 `order_by` + `where`？
  - [ ] 是否使用多个 `where` 条件？
  - [ ] 是否使用 `where` + `order_by` + 不同的字段？

- [ ] **检查索引需求**
  - [ ] 是否需要复合索引？
  - [ ] 索引字段是什么？
  - [ ] 索引顺序是什么（ASC/DESC）？

- [ ] **配置索引**
  - [ ] 索引已添加到 `firestore.indexes.json`
  - [ ] 索引配置正确（字段、顺序）
  - [ ] 索引范围正确（Collection/CollectionGroup）

- [ ] **添加回退方案**
  - [ ] 如果索引未就绪，是否有回退方案？
  - [ ] 回退方案是否测试过？
  - [ ] 回退方案是否有日志记录？

- [ ] **添加注释**
  - [ ] 函数注释说明索引需求
  - [ ] 代码注释说明查询模式
  - [ ] 提供索引创建链接（如果可能）

### 🔍 代码审查阶段

**代码审查时检查**：

- [ ] **查询模式检查**
  - [ ] 查询模式是否正确？
  - [ ] 是否需要索引？
  - [ ] 索引配置是否正确？

- [ ] **索引配置检查**
  - [ ] `firestore.indexes.json` 中是否有对应索引？
  - [ ] 索引字段和顺序是否匹配？
  - [ ] 索引范围是否正确？

- [ ] **回退方案检查**
  - [ ] 是否有回退方案？
  - [ ] 回退方案是否合理？
  - [ ] 回退方案是否有测试？

- [ ] **测试覆盖检查**
  - [ ] 是否有单元测试？
  - [ ] 是否有集成测试？
  - [ ] 测试是否覆盖索引依赖？

### 🧪 测试阶段

**测试时验证**：

- [ ] **功能测试**
  - [ ] 查询功能是否正常？
  - [ ] 查询结果是否正确？
  - [ ] 错误处理是否正确？

- [ ] **索引依赖测试**
  - [ ] 索引是否存在？
  - [ ] 索引状态是否为 "Enabled"？
  - [ ] 查询是否可用（需要索引时）？

- [ ] **回退方案测试**
  - [ ] 回退方案是否可用？
  - [ ] 回退方案是否正确？
  - [ ] 回退方案是否有日志？

- [ ] **集成测试**
  - [ ] 端到端测试是否通过？
  - [ ] 自动触发流程是否正常？
  - [ ] 错误场景是否处理？

### 🚀 部署阶段

**部署前验证**：

- [ ] **索引部署**
  - [ ] 索引已添加到 `firestore.indexes.json`
  - [ ] 索引已部署：`firebase deploy --only firestore:indexes`
  - [ ] 索引状态为 "Enabled"（或 "Building"）

- [ ] **功能验证**
  - [ ] 查询功能正常
  - [ ] 回退方案可用（如果索引未就绪）
  - [ ] 日志记录正确

- [ ] **监控设置**
  - [ ] 监控查询失败率
  - [ ] 监控索引构建状态
  - [ ] 设置告警（如果查询失败）

## 通用开发检查清单

### 📝 代码编写

- [ ] 代码符合项目规范
- [ ] 添加必要的注释
- [ ] 错误处理完善
- [ ] 日志记录充分

### 🔍 代码审查

- [ ] 代码逻辑正确
- [ ] 性能考虑合理
- [ ] 安全性检查通过
- [ ] 测试覆盖充分

### 🧪 测试

- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 端到端测试通过
- [ ] 错误场景测试通过

### 🚀 部署

- [ ] 依赖已更新
- [ ] 配置已更新
- [ ] 数据库迁移（如需要）
- [ ] 索引已部署（如需要）

## Firestore 查询模式识别

### 需要索引的模式

1. **`where` + `order_by`**（不同字段）
   ```python
   query = collection.where("field1", "==", value).order_by("field2")
   # 需要索引：field1 (ASC) + field2 (DESC)
   ```

2. **多个 `where` + `order_by`**
   ```python
   query = collection.where("field1", "==", value1).where("field2", "==", value2).order_by("field3")
   # 需要索引：field1 (ASC) + field2 (ASC) + field3 (DESC)
   ```

3. **`where` + `order_by`（相同字段，但顺序不同）**
   ```python
   query = collection.where("field1", ">", value).order_by("field1")
   # 需要索引：field1 (ASC) 或 field1 (DESC)
   ```

### 不需要索引的模式

1. **单个 `where`**
   ```python
   query = collection.where("field1", "==", value)
   # 不需要索引（单字段索引自动创建）
   ```

2. **单个 `order_by`**
   ```python
   query = collection.order_by("field1")
   # 不需要索引（单字段索引自动创建）
   ```

3. **`where` + `order_by`（相同字段，相同顺序）**
   ```python
   query = collection.where("field1", ">", value).order_by("field1")
   # 不需要索引（单字段索引自动创建）
   ```

## 索引配置模板

### firestore.indexes.json 格式

```json
{
  "indexes": [
    {
      "collectionGroup": "collection_name",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "field1",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "field2",
          "order": "DESCENDING"
        }
      ]
    }
  ]
}
```

### 索引部署命令

```bash
# 部署索引
firebase deploy --only firestore:indexes --project fleet-blend-469520-n7

# 查看索引状态
# https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore/indexes
```

## 回退方案模板

### 代码模板

```python
def query_with_fallback():
    """Query with fallback mechanism."""
    try:
        # Try database-level sorting (requires index)
        query = collection.where("field1", "==", value).order_by("field2")
        return query.stream()
    except Exception as exc:
        if "index" in str(exc).lower():
            # Fallback to memory sorting
            logger.warning("Index not ready, using memory sorting")
            return query_with_memory_sorting()
        raise
```

## 提醒模板

### 代码审查提醒

```
⚠️ **Firestore 索引检查**

这个查询需要复合索引：
- Collection: `collection_name`
- Fields: `field1` (ASC) + `field2` (DESC)

请确认：
- [ ] 索引已添加到 `firestore.indexes.json`
- [ ] 索引已部署
- [ ] 索引状态为 "Enabled"
- [ ] 有回退方案（如果索引未就绪）
```

### 开发提醒

```
💡 **提醒**

您正在使用需要索引的查询模式。
请：
1. 添加索引到 `firestore.indexes.json`
2. 部署索引
3. 添加回退方案
```

