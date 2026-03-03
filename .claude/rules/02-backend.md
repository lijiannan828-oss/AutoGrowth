# 后端开发规则

## API Route 规范

所有 API 放在 `src/app/api/` 目录下，使用 Next.js App Router 格式。

```typescript
// ✅ 正确示例：src/app/api/generate/image/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const params = await request.json();

    // 业务逻辑...

    return NextResponse.json({
      success: true,
      data: { image_url: '...' },
    });
  } catch (error) {
    console.error('[API] Error:', error);
    return NextResponse.json({
      success: false,
      error: { message: '错误信息' },
    }, { status: 500 });
  }
}
```

---

## API 响应格式

```typescript
// 成功响应
{
  success: true,
  data: { ... }
}

// 错误响应
{
  success: false,
  error: {
    code: 'ERROR_CODE',
    message: '用户可读的错误信息',
    details: '详细错误信息（可选）'
  }
}
```

---

## 日志规范

使用 `console.log` 进行调试，格式为 `[模块名] 消息`：

```typescript
console.log('[Vertex AI] Using Imagen 3 for image generation');
console.log('[API] Generate image with model:', model);
console.error('[API] ❌ Error:', error);
console.warn('[API] ⚠️ Warning:', message);
```
