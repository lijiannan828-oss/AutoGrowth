# API 使用检查清单

在使用新的 Google Cloud API 之前，请按照以下清单进行检查：

## ✅ 使用新 API 前的检查步骤

### 1. 查阅官方文档
- [ ] 确认正确的客户端类（如 `JobsClient` vs `ExecutionsClient`）
- [ ] 确认方法名和参数
- [ ] 查看返回值的结构

**资源**:
- [Google Cloud Run v2 Python API 文档](https://cloud.google.com/python/docs/reference/run/latest)
- [Google Cloud API Explorer](https://cloud.google.com/apis/design)

### 2. 验证方法存在性
```python
# 检查方法是否存在
client = SomeClient()
print(hasattr(client, 'method_name'))  # 应该是 True
```

### 3. 检查返回对象结构
```python
# 列出返回对象的所有属性
result = client.some_method(...)
print(dir(result))  # 查看所有属性
print(hasattr(result, 'expected_attr'))  # 验证属性存在
```

### 4. 获取完整详情（如需要）
```python
# 如果 list 方法返回的是简化对象，使用 get 方法获取详情
list_result = client.list_items(...)
for item in list_result.items:
    full_item = client.get_item(name=item.name)
    # 现在可以访问完整属性
```

### 5. 检查属性名
```python
# Protobuf 生成的代码可能使用下划线后缀
# 使用 dir() 检查实际属性名
obj = ...
attrs = [a for a in dir(obj) if not a.startswith('_')]
print(attrs)  # 查看所有属性
```

### 6. 编写探索脚本
```python
# 创建临时脚本探索 API 结构
# backend/scripts/explore_xxx_api.py
```

### 7. 编写单元测试
```python
# 为关键 API 调用编写测试
# backend/tests/test_xxx_service.py
```

## ⚠️ 常见陷阱

1. **客户端选择错误**
   - ❌ `JobsClient.list_executions()` - 不存在
   - ✅ `ExecutionsClient.list_executions()` - 正确

2. **假设对象结构**
   - ❌ 假设 `list_executions()` 返回完整对象
   - ✅ 使用 `get_execution()` 获取完整详情

3. **属性名猜测**
   - ❌ `condition.type` - 不存在
   - ✅ `condition.type_` - 正确

4. **字段用途错误**
   - ❌ `condition.reason` - 是枚举值，不是消息
   - ✅ `condition.message` - 包含人类可读的消息

## 📝 代码审查检查点

在代码审查时，检查以下内容：

- [ ] 是否使用了正确的客户端类？
- [ ] 调用的方法是否确实存在？
- [ ] 访问的属性是否确实存在？
- [ ] 是否正确处理了返回值？
- [ ] 是否有适当的错误处理？
- [ ] 是否进行了实际测试验证？

## 🔧 工具和资源

1. **探索脚本**: `backend/scripts/explore_run_v2_api.py`
2. **API 使用指南**: `backend/docs/API_USAGE_GUIDE.md`
3. **错误分析**: `backend/scripts/API_USAGE_ERROR_ANALYSIS.md`
