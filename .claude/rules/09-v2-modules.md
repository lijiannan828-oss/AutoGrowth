# v2.0 功能模块规范

> **更新日期**：2026-02-27

---

## 路由规范

v2.0 新增路由必须严格遵守以下前缀，**禁止**与现有 `/canvas` 路由冲突：

| 路由 | 页面文件 | 说明 |
|------|----------|------|
| `/series/[series_id]/setup` | `src/app/series/[series_id]/setup/page.tsx` | Series Setup 5步向导 |
| `/series/[series_id]/assets/[asset_id]/canvas` | `src/app/series/[series_id]/assets/[asset_id]/canvas/page.tsx` | 人物/场景/道具资产画布 |

- ❌ **禁止**在 `src/app/canvas/` 目录下挂载任何 Series Setup 相关页面
- ❌ **禁止**将 `/series` 路由组件混入现有 `src/app/workspace/` 目录
- 资产画布使用**独立** ReactFlow 实例，不复用主画布的 `FlowCanvas` 组件

---

## Series Setup 向导状态机规范

向导步骤状态使用 **React Context + Reducer + 脏标记**管理，不得使用全局 Zustand Store。

```typescript
// src/app/series/[series_id]/setup/context/SetupContext.tsx
'use client';

type Step = 0 | 1 | 2 | 3 | 4;
// 0=导入剧本  1=选择风格  2=生成图片资产  3=生成人物音色  4=生成剧集

interface StepState {
  data: Record<string, unknown>;
  dirty: boolean;     // true = 回退后需重新完成
  completed: boolean;
}

type SetupAction =
  | { type: 'GO_TO_STEP'; step: Step }
  | { type: 'COMPLETE_STEP'; step: Step; data: Record<string, unknown> }
  | { type: 'MARK_DIRTY_FROM'; step: Step }; // 回退时将该步骤及之后全部标记 dirty
```

**规则**：
- 用户点击"上一步"时**必须**调用 `MARK_DIRTY_FROM`，将当前步骤及之后所有步骤标记 dirty
- 步骤数据在 `COMPLETE_STEP` 时落库（调用 Firestore），不在中途写入
- 每步完成时通过 Zod schema 做增量校验，确保数据合法后再落库
- `series_setup` 文档的 `status` 字段：
  - 向导进行中：`'in_progress'`
  - 第5步完成后：`'completed'`

---

## 风格库（`styles` 集合）读写规范

风格库为全局共享集合，共 33 条预设数据，**前端只读**，由后台脚本初始化。

```typescript
// ✅ 正确：从 styles 集合读取
export async function getStyles(): Promise<Style[]> {
  const snapshot = await getDocs(collection(db, 'styles'));
  return snapshot.docs.map(d => ({ id: d.id, ...d.data() })) as Style[];
}

// ❌ 禁止：前端直接写入 styles 集合
await addDoc(collection(db, 'styles'), { ... }); // 禁止
await updateDoc(doc(db, 'styles', id), { ... }); // 禁止（除非是后台 API Route）
```

**Seed 注入**（仅在后台 API Route 中，幂等写入）：

```typescript
// src/app/api/admin/seed-styles/route.ts
// 文档不存在时写入，已存在且 user_modified=true 时跳过
async function seedStyleIfNeeded(styleId: string, data: StyleData) {
  const ref = doc(db, 'styles', styleId);
  const snap = await getDoc(ref);
  if (snap.exists() && snap.data().user_modified === true) return; // 跳过用户已修改的
  if (!snap.exists()) {
    await setDoc(ref, { ...data, seeded_at: serverTimestamp() });
  }
}
```

- Seed 完成后前端必须使相关缓存失效（如使用 React Query：`queryClient.invalidateQueries(['styles'])`）
- `cover_url` 为空时前端显示"封面生成中"占位，后端异步生成后轮询刷新

---

## Firestore 新增集合命名规范

v2.0 新增集合一律使用 **snake_case**：

| 集合名 | 服务层文件 | 说明 |
|--------|-----------|------|
| `series_setup` | `src/lib/firebase/series-setup.ts` | 向导配置（每个 series 一条） |
| `styles` | `src/lib/firebase/styles.ts` | 全局风格库（33条，只读） |
| `character_variants` | `src/lib/firebase/character-variants.ts` | 人物变体资产 |
| `scene_assets` | `src/lib/firebase/scene-assets.ts` | 场景资产 |
| `prop_assets` | `src/lib/firebase/prop-assets.ts` | 道具资产 |
| `shot_node_bindings` | `src/lib/firebase/shot-node-bindings.ts` | 分镜与节点 1:1 绑定 |
| `video_remake_groups` | `src/lib/firebase/video-remake.ts` | 视频重制任务组 |
| `video_remake_variants` | `src/lib/firebase/video-remake.ts` | 重制变体 |
| `idempotency_keys` | （内部使用，无独立服务层） | 请求幂等键，TTL 24h |

- ❌ 禁止使用 camelCase 或 PascalCase 命名集合（如 `seriesSetup`、`StyleConfig`）
- 每个集合的服务层文件放在 `src/lib/firebase/` 下，与现有文件并列

---

## 资产落库必填字段规范

所有 v2.0 资产写入 Firestore 时，以下字段**必填**，缺少任一字段的写入必须被拦截：

```typescript
interface V2AssetBase {
  series_id: string;       // 必填：归属剧集
  created_by: string;      // 必填：创建者 userId
  prompt_snapshot: string; // 必填：生成时使用的完整最终提示词（含风格注入）
  model_snapshot: string;  // 必填：生成时使用的模型名称和版本（如 "imagen-3.0"）
  asset_type: 'character' | 'scene' | 'prop' | 'music' | 'remake';
  created_at: Timestamp;   // 必填：serverTimestamp()
  episode_id?: string;     // Series Setup 阶段为空，进入集制作后填写
}
```

- `prompt_snapshot` 必须是注入风格 `style_prompt_prefix` 后的**完整 FINAL_PROMPT**，不得存储用户原始输入
- 事后修改提示词时，`prompt_snapshot` **不得**回写（保留生成时快照用于追溯）

---

## 音乐节点（MusicNode）实现规范

**文件位置**：

```
src/components/nodes/MusicNode.tsx      # 节点 UI 组件
src/lib/firebase/music-assets.ts        # 数据服务层
src/app/api/generate/music/route.ts     # 生成 API
```

**节点数据结构**：

```typescript
interface MusicNodeData {
  nodeType: 'music';
  mode: 'tts' | 'bgm';                    // 文字转语音 | 背景音乐
  duration: 'auto' | 30 | 60 | 120 | 180 | 240; // 秒，auto 表示 AI 自行判断
  model: string;                           // 模型标识，如 'elevenlabs-v3'
  voiceId?: string;                        // TTS 时指定音色 ID
  pureMusic?: boolean;                     // bgm 模式时是否纯音乐（无人声）
  status: 'idle' | 'generating' | 'done' | 'error';
  audio_url?: string;
  prompt_snapshot: string;                 // 必填，见资产落库规范
  series_id: string;                       // 必填
}
```

**连线规则**：
- MusicNode 只能作为**目标节点**（target），接收来自 CardNode / VideoNode / TextNode 的连线
- 人物资产画布中的音色节点，**只能**连接对应角色的 CharacterBriefNode（简介节点）
- ❌ MusicNode 之间不得互连
- ❌ MusicNode 不得作为源节点连接其他节点

**右键菜单注册**：在 `src/components/canvas/ContextMenu.tsx` 中统一添加"添加音乐节点"入口，**不得**在其他位置散布菜单项。

---

## 视频重制节点（VideoRemakeNode）实现规范

**文件位置**：

```
src/components/nodes/VideoRemakeNode.tsx
src/lib/firebase/video-remake.ts
src/app/api/generate/video-remake/route.ts
```

**Slash 指令解析**：

```typescript
// 在 VideoRemakeNode 输入框中解析
const REMAKE_COMMANDS = {
  '/remake 1': 'single',    // 单版本
  '/remake 4': 'grid_2x2', // 四宫格
  '/remake 9': 'grid_3x3', // 九宫格
} as const;

type RemakeLayout = (typeof REMAKE_COMMANDS)[keyof typeof REMAKE_COMMANDS];
```

**节点数据结构**：

```typescript
interface VideoRemakeNodeData {
  nodeType: 'video_remake';
  layout: 'single' | 'grid_2x2' | 'grid_3x3';
  source_video_id: string;    // 上游视频节点 ID
  similarity_score?: number;  // 生成后回填，必须在 [0.60, 0.85]
  dedup_dimensions: string[]; // 去重维度，至少 5 个
  prompt_text: string;        // 用户输入（含默认模板）
  status: 'idle' | 'generating' | 'done' | 'partial_failed' | 'failed';
  series_id: string;
  prompt_snapshot: string;    // 必填
}
```

**前端强制校验**（提交 API 前必须通过）：
- `similarity_score` 不在 `[0.60, 0.85]` 范围内 → toast 提示，**不得**提交
- `dedup_dimensions.length < 5` → toast 提示，**不得**提交
- 上游视频节点未完成（generating/failed）→ 生成按钮置灰，tooltip 提示原因
