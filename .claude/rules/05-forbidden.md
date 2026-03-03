# 禁止事项

## 代码规范禁止

```typescript
// ❌ 禁止：在 Firestore 中存储 undefined
await addDoc(collection, { name: undefined }); // 会报错

// ❌ 禁止：客户端组件缺少 'use client'
// 会导致 hooks 无法使用

// ❌ 禁止：直接修改 state
set((state) => {
  state.tasks.set(id, task); // ❌ 直接修改
  return state;
});

// ✅ 正确：创建新对象
set((state) => {
  const newTasks = new Map(state.tasks);
  newTasks.set(id, task);
  return { tasks: newTasks };
});
```

---

## API 禁止

- ❌ 禁止在 API 中返回随机 fallback 图片（失败时应返回错误）
- ❌ 禁止硬编码 API 密钥（使用环境变量）
- ❌ 禁止忽略错误（必须 catch 并记录日志）

---

## 样式禁止

- ❌ 禁止使用内联样式（使用 Tailwind CSS）
- ❌ 禁止使用 `!important`（除非覆盖第三方库）
