# 前端开发规则

## 组件规范

```typescript
// ✅ 客户端组件必须添加 'use client'
'use client';

import { memo, useState, useCallback } from 'react';

// 使用 memo 优化性能
export const CardNode = memo(function CardNode({ id, data }: Props) {
  const [isHovered, setIsHovered] = useState(false);

  // 使用 useCallback 缓存回调
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  return (
    <div onClick={handleClick}>
      {/* 组件内容 */}
    </div>
  );
});
```

---

## 状态管理 (Zustand)

```typescript
// src/lib/store/generation-store.ts
import { create } from 'zustand';

interface GenerationState {
  tasks: Map<string, GenerationTask>;
  startGeneration: (params: GenerationParams) => Promise<string>;
  updateTask: (taskId: string, updates: Partial<GenerationTask>) => void;
}

export const useGenerationStore = create<GenerationState>((set, get) => ({
  tasks: new Map(),

  startGeneration: async (params) => {
    // 实现...
  },

  updateTask: (taskId, updates) => {
    set((state) => {
      const newTasks = new Map(state.tasks);
      const existing = newTasks.get(taskId);
      if (existing) {
        newTasks.set(taskId, { ...existing, ...updates });
      }
      return { tasks: newTasks };
    });
  },
}));
```

---

## 自定义 Hook 规范

```typescript
// src/lib/hooks/useAuth.ts
'use client';

import { useState, useEffect, useCallback } from 'react';

interface UseAuthReturn {
  user: User | null;
  loading: boolean;
  error: string | null;
  signIn: () => Promise<void>;
  logout: () => Promise<void>;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthChange((user) => {
      setUser(user);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  return { user, loading, error, signIn, logout };
}
```
