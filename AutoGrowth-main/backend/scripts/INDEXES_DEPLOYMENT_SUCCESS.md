# Firestore 索引部署成功 ✅

## 部署时间

**2025-11-22**

## 部署结果

✅ **成功部署 9 个 Firestore 复合索引**

### 索引列表

#### pipeline_jobs 集合 (7 个索引)

1. ✅ `drama_name` (ASC) + `updated_at` (DESC)
2. ✅ `status` (ASC) + `updated_at` (DESC)
3. ✅ `stage` (ASC) + `updated_at` (DESC)
4. ✅ `drama_name` (ASC) + `status` (ASC) + `updated_at` (DESC)
5. ✅ `drama_name` (ASC) + `stage` (ASC) + `updated_at` (DESC)
6. ✅ `transfer_completed` (ASC) + `updated_at` (DESC)
7. ✅ `drama_name` (ASC) + `transfer_completed` (ASC) + `updated_at` (DESC)

#### google_oauth_tokens 集合 (2 个索引)

8. ✅ `userId` (ASC) + `updatedAt` (DESC)
9. ✅ `userEmail` (ASC) + `updatedAt` (DESC)

## 索引状态

索引正在构建中，通常需要 **1-5 分钟** 完成。

### 查看索引状态

**方法 1: Firebase Console**
```
https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore/indexes
```

**方法 2: gcloud CLI**
```bash
gcloud firestore indexes list --project=fleet-blend-469520-n7
```

**索引状态说明**:
- **Building**: 正在构建（等待）
- **Enabled**: 已启用，可以使用 ✅
- **Error**: 构建失败（需要检查）

## 下一步操作

### 1. 等待索引构建完成

索引构建完成后（状态变为 "Enabled"），可以：

### 2. 恢复使用 `order_by` 查询

修改 `backend/app/api/v1/relay.py` 中的 `_find_latest_ready_job` 函数：

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

### 3. 验证索引工作正常

运行测试脚本验证索引是否正常工作：

```bash
python3 backend/scripts/test_relay_service.py
```

## 相关文件

- ✅ `firestore.indexes.json`: 索引配置文件
- ✅ `firebase.json`: Firebase 项目配置
- ✅ `firestore.rules`: Firestore 安全规则（基本配置）
- ✅ `backend/scripts/create_firestore_indexes.sh`: 索引创建脚本
- ✅ `backend/scripts/FIRESTORE_INDEXES_GUIDE.md`: 索引创建指南

## 注意事项

1. **索引构建时间**: 索引构建可能需要几分钟，请耐心等待
2. **索引成本**: 索引占用存储空间，但通常很小（每个索引几 KB）
3. **自动维护**: Firestore 自动维护索引，无需手动更新
4. **查询性能**: 使用索引后，查询性能会显著提升

## 故障排除

如果索引构建失败或查询仍然失败：

1. **检查索引状态**: 确认所有索引状态为 "Enabled"
2. **检查查询条件**: 确认查询条件与索引匹配
3. **查看错误消息**: 错误消息中可能包含索引创建链接
4. **重新部署**: 如果索引构建失败，可以重新运行部署命令

## 总结

✅ **索引已成功部署**
- 9 个复合索引已创建
- 索引正在构建中
- 构建完成后即可使用 `order_by` 查询

🎯 **下一步**: 等待索引构建完成，然后恢复使用 `order_by` 查询代码


