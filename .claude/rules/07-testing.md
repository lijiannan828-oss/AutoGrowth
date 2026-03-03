# 测试规范

## 文件组织

所有测试文件必须放在 `src/__tests__/` 目录下：

```
src/__tests__/
├── setup.ts              # 测试环境配置
├── components/           # 组件测试
│   ├── CardNode.test.tsx
│   └── FlowCanvas.test.tsx
├── hooks/                # Hook 测试
│   └── useGeneration.test.ts
├── store/                # Store 测试
│   └── generation-store.test.ts
├── api/                  # API 测试
│   └── generate-image.test.ts
└── utils/                # 工具函数测试
    └── helpers.test.ts
```

---

## 命名规范

- 测试文件：`*.test.ts` 或 `*.test.tsx`
- 测试描述使用中文

```typescript
describe('CardNode 组件', () => {
  it('应该正确渲染卡片标题', () => {
    // ...
  });
});
```

---

## 测试框架

- **测试运行器**: Vitest
- **组件测试**: @testing-library/react
- **DOM 环境**: jsdom

---

## 测试模式

### 组件测试

```typescript
import { render, screen } from '@testing-library/react';
import { CardNode } from '@/components/nodes/CardNode';

describe('CardNode 组件', () => {
  it('应该显示节点标题', () => {
    render(<CardNode data={{ title: '测试节点' }} />);
    expect(screen.getByText('测试节点')).toBeInTheDocument();
  });
});
```

### Hook 测试

```typescript
import { renderHook, act } from '@testing-library/react';
import { useGenerationStore } from '@/lib/store/generation-store';

describe('useGenerationStore', () => {
  it('应该正确添加任务', () => {
    const { result } = renderHook(() => useGenerationStore());

    act(() => {
      result.current.addTask({ id: '1', status: 'pending' });
    });

    expect(result.current.tasks.size).toBe(1);
  });
});
```

### API 测试

```typescript
import { POST } from '@/app/api/generate/image/route';

describe('图片生成 API', () => {
  it('应该返回成功响应', async () => {
    const request = new Request('http://localhost/api/generate/image', {
      method: 'POST',
      body: JSON.stringify({ prompt: '测试提示词' }),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(data.success).toBe(true);
  });
});
```

---

## 运行测试

```bash
# 运行所有测试
npm run test

# 监听模式
npm run test:watch

# 生成覆盖率报告
npm run test:coverage
```

---

## 禁止事项

- ❌ 禁止在 `src/__tests__/` 以外的地方放置测试文件
- ❌ 禁止测试文件中硬编码敏感信息
- ❌ 禁止跳过失败的测试（除非有明确注释说明原因）
