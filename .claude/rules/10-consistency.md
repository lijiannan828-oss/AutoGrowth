# v2.0 数据一致性规范

> **更新日期**：2026-02-27

---

## 风格权重平衡算法

每次用户调整任意风格权重，前端必须**实时重算**，保证：

1. 所有风格权重之和 = **100**（整数，单位 %，禁止浮点数）
2. 主风格权重 ≥ **50**
3. 每个辅助风格权重 ≤ **50**，且二者之和 ≤ 50

```typescript
// src/lib/utils/style-weight.ts

export interface StyleWeight {
  style_id: string;
  weight: number; // 整数，%，范围 [0, 100]
}

/**
 * 调整某条权重后，按比例重算其余权重，保证总和 = 100
 * @param weights   当前所有风格权重数组（主风格排第0位）
 * @param changedId 被用户修改的风格 id
 * @param newWeight 用户设置的新权重（整数 %）
 */
export function rebalanceWeights(
  weights: StyleWeight[],
  changedId: string,
  newWeight: number,
): StyleWeight[] {
  const clamped = Math.min(Math.max(Math.round(newWeight), 0), 100);
  const others = weights.filter(w => w.style_id !== changedId);
  const remainder = 100 - clamped;
  const othersTotal = others.reduce((s, w) => s + w.weight, 0);

  const rebalanced = others.map(w => ({
    ...w,
    weight: othersTotal === 0
      ? Math.floor(remainder / others.length)
      : Math.round((w.weight / othersTotal) * remainder),
  }));

  // 修正舍入误差，补到权重最大的那条
  const actualRemainder = rebalanced.reduce((s, w) => s + w.weight, 0);
  const diff = remainder - actualRemainder;
  if (diff !== 0 && rebalanced.length > 0) {
    const maxIdx = rebalanced.reduce((mi, w, i) => w.weight > rebalanced[mi].weight ? i : mi, 0);
    rebalanced[maxIdx].weight += diff;
  }

  return [{ style_id: changedId, weight: clamped }, ...rebalanced];
}

/** 提交前校验，任一失败返回 false */
export function validateStyleWeights(weights: StyleWeight[]): boolean {
  const total = weights.reduce((s, w) => s + w.weight, 0);
  const primaryWeight = weights[0]?.weight ?? 0; // 约定主风格排第0位
  return total === 100 && primaryWeight >= 50;
}
```

**后端二次校验**（API Route 中使用 Zod）：

```typescript
import { z } from 'zod';

const StyleWeightSchema = z.object({
  style_id: z.string().min(1),
  weight: z.number().int().min(0).max(100),
});

export const WeightsPayloadSchema = z.array(StyleWeightSchema)
  .min(1)
  .refine(ws => ws.reduce((s, w) => s + w.weight, 0) === 100, {
    message: '权重总和必须等于 100',
  })
  .refine(ws => (ws[0]?.weight ?? 0) >= 50, {
    message: '主风格（数组第0项）权重必须 ≥ 50%',
  });
```

- ❌ 禁止只做前端校验跳过后端 Zod 校验
- ❌ 禁止权重字段使用浮点数（`weight: 33.33` → 错误，应为整数 `33`）

---

## 批量写入必须使用 Firestore 事务

Series Setup 每步完成时的落库，以及所有批量创建操作，**必须**使用 `runTransaction` 或 `writeBatch`：

```typescript
import { runTransaction, writeBatch, doc } from 'firebase/firestore';

// ✅ 正确：事务性原子写入
async function completeSetupStep(seriesId: string, stepData: unknown, nextStatus: string) {
  await runTransaction(db, async (tx) => {
    const setupRef = doc(db, 'series_setup', seriesId);
    const snap = await tx.get(setupRef);
    if (!snap.exists()) throw new Error('series_setup 不存在');

    tx.update(setupRef, {
      ...stepData as object,
      status: nextStatus,
      updated_at: serverTimestamp(),
    });
  });
}

// ❌ 禁止：分两次独立 updateDoc（断线时会导致部分写入）
await updateDoc(setupRef, { step_data: data });
await updateDoc(seriesRef, { status: 'step_done' }); // ❌
```

**批量条数限制**：
- 单次 `writeBatch` 最多 **499** 条写操作（Firestore 限制为 500，留 1 条余量）
- 超过 499 条时，分批提交，每批独立 commit

---

## 分镜 1:1 绑定规范（`shot_node_bindings`）

分镜行与画布节点之间是严格的 **1:1** 关系，通过 `shot_node_bindings` 中间表维护。

**文档结构**：

```typescript
interface ShotNodeBinding {
  id: string;          // Firestore 文档 ID
  shot_id: string;     // 唯一：每条分镜只能绑定一个节点
  node_id: string;     // 唯一：每个节点只能绑定一条分镜
  episode_id: string;
  series_id: string;
  bound_by: string;    // 操作者 userId
  created_at: Timestamp;
}
```

**创建绑定的标准流程**（事务内双向检查）：

```typescript
async function createShotNodeBinding(
  shotId: string,
  nodeId: string,
  episodeId: string,
  seriesId: string,
  userId: string,
) {
  await runTransaction(db, async (tx) => {
    // 1. 检查 shot_id 是否已被绑定
    const byShot = await getDocs(
      query(collection(db, 'shot_node_bindings'), where('shot_id', '==', shotId))
    );
    if (!byShot.empty) throw new Error(`shot ${shotId} 已绑定节点，请先解绑`);

    // 2. 检查 node_id 是否已被绑定
    const byNode = await getDocs(
      query(collection(db, 'shot_node_bindings'), where('node_id', '==', nodeId))
    );
    if (!byNode.empty) throw new Error(`node ${nodeId} 已绑定分镜，请先解绑`);

    // 3. 写入绑定
    tx.set(doc(collection(db, 'shot_node_bindings')), {
      shot_id: shotId,
      node_id: nodeId,
      episode_id: episodeId,
      series_id: seriesId,
      bound_by: userId,
      created_at: serverTimestamp(),
    });
  });
}
```

**删除节点时的级联清理**：

```typescript
// 删除节点时必须同步删除绑定记录
async function deleteNodeWithBinding(nodeId: string) {
  await runTransaction(db, async (tx) => {
    // 查找并删除对应绑定
    const bindings = await getDocs(
      query(collection(db, 'shot_node_bindings'), where('node_id', '==', nodeId))
    );
    bindings.docs.forEach(d => tx.delete(d.ref));
    // 继续删除节点本身（根据实际数据结构）
  });
}
```

- ❌ 禁止直接在 shot 文档或 node 数据上存储对方 ID（必须通过中间表）
- ❌ 禁止只删除节点而遗留孤儿绑定记录

---

## 剧集批量创建防重复规范

Series Setup 第5步批量创建剧集时，必须按以下顺序执行：

```
1. 预校验（事务外）：风格配置已完成、资产存在性
        ↓
2. 事务内查询当前最大 episode_number
        ↓
3. 从 max + 1 开始递增写入
        ↓
4. 返回成功/失败明细 { success: string[], failed: string[] }
```

```typescript
async function batchCreateEpisodes(seriesId: string, count: number): Promise<{
  success: string[];
  failed: Array<{ number: number; reason: string }>;
}> {
  // 1. 事务外预校验
  const setupSnap = await getDoc(doc(db, 'series_setup', seriesId));
  if (!setupSnap.data()?.step2_completed) {
    throw new Error('风格配置未完成，无法批量创建剧集');
  }

  // 2. 事务内写入
  const created: string[] = [];
  await runTransaction(db, async (tx) => {
    const existingEps = await getDocs(
      query(collection(db, 'episodes'), where('series_id', '==', seriesId))
    );
    const maxNum = existingEps.docs.reduce(
      (max, d) => Math.max(max, d.data().episode_number ?? 0), 0
    );

    for (let i = 1; i <= count; i++) {
      const ref = doc(collection(db, 'episodes'));
      tx.set(ref, {
        series_id: seriesId,
        episode_number: maxNum + i,
        status: 'draft',
        created_at: serverTimestamp(),
      });
      created.push(ref.id);
    }
  });

  return { success: created, failed: [] };
}
```

- **防重复**：已存在集时（`episode_count > 0`），禁止再次触发批量创建，前端提前拦截并 toast 提示
- 部分失败时返回 `{ success, failed }` 明细，前端展示"成功 x / 失败 y"并提供"重试失败项"

---

## 双向定位防循环规范（`lockRef` 模式）

分镜表与画布节点双向联动时，**必须**使用 `lockRef + requestAnimationFrame` 防止事件循环。

```typescript
// src/lib/hooks/useBidirectionalSync.ts
import { useRef, useCallback } from 'react';

export function useBidirectionalSync() {
  const lockRef = useRef(false);

  /** 画布节点点击 → 分镜表高亮 */
  const syncFromCanvas = useCallback((nodeId: string, scrollToShot: (id: string) => void) => {
    if (lockRef.current) return; // 阻断反向触发
    lockRef.current = true;
    scrollToShot(nodeId);
    requestAnimationFrame(() => { lockRef.current = false; });
  }, []);

  /** 分镜表行点击 → 画布节点聚焦 */
  const syncFromStoryboard = useCallback((shotId: string, focusNode: (id: string) => void) => {
    if (lockRef.current) return;
    lockRef.current = true;
    focusNode(shotId);
    requestAnimationFrame(() => { lockRef.current = false; });
  }, []);

  return { syncFromCanvas, syncFromStoryboard };
}
```

- ❌ 禁止使用 `setTimeout` 替代 `requestAnimationFrame`（时序不可靠）
- ❌ 禁止在 `useEffect` 依赖数组中放入会循环更新的 state 值
- 每次联动只触发**单向**同步，由 `lockRef` 保证另一侧不反向触发

---

## 请求幂等键规范

所有**生成类** API 请求必须携带幂等键，防止用户重复点击或网络重试导致重复计费/重复生成。

**客户端发送**：

```typescript
// 每次点击"生成"时生成新 UUID
const idempotencyKey = crypto.randomUUID();

await fetch('/api/generate/music', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Idempotency-Key': idempotencyKey,
  },
  body: JSON.stringify(params),
});
```

**API Route 中校验**：

```typescript
// 在 src/app/api/generate/*/route.ts 中统一处理
const key = request.headers.get('X-Idempotency-Key');
if (!key) {
  return NextResponse.json(
    { success: false, error: { message: '缺少 X-Idempotency-Key 请求头' } },
    { status: 400 }
  );
}

const existing = await getDoc(doc(db, 'idempotency_keys', key));
if (existing.exists()) {
  // 直接返回已缓存的结果（幂等响应）
  return NextResponse.json({ success: true, data: existing.data()?.result });
}

// 正常执行生成逻辑，完成后写入幂等键
await setDoc(doc(db, 'idempotency_keys', key), {
  result: generatedResult,
  expires_at: Timestamp.fromMillis(Date.now() + 24 * 60 * 60 * 1000), // 24h TTL
});
```

**适用范围**：

| API | 需要幂等键 |
|-----|-----------|
| `/api/generate/image` | ✅ |
| `/api/generate/video` | ✅ |
| `/api/generate/music` | ✅ |
| `/api/generate/video-remake` | ✅ |
| `/api/upload/*` | ✅ |
| `/api/queue/*`（查询状态） | ❌ 天然幂等 |
| `/api/canvas/*`（读取） | ❌ 天然幂等 |

- `idempotency_keys` 集合需在 Firebase Console 配置 TTL 策略（`expires_at` 字段，24h 自动删除）
