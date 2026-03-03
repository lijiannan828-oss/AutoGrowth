# v2.0 高风险文件 + UI 扩展规范

> **更新日期**：2026-02-27

---

## v2.0 新增高风险文件

以下文件是 v2.0 阶段新增的复杂核心文件，**禁止**未经沟通直接修改：

| 文件 | 预计行数 | 原因 |
|------|----------|------|
| `src/app/series/[series_id]/setup/page.tsx` | ~600 | Series Setup 向导主入口，含状态机路由逻辑 |
| `src/app/series/[series_id]/setup/context/SetupContext.tsx` | ~200 | 向导 Context + Reducer，所有步骤共用 |
| `src/components/nodes/MusicNode.tsx` | ~400 | 含 TTS/BGM 双模式 + 音色选择逻辑 |
| `src/components/nodes/VideoRemakeNode.tsx` | ~450 | 含 slash 指令解析 + 相似度校验 |
| `src/app/series/[series_id]/assets/[asset_id]/canvas/page.tsx` | ~500 | 资产画布主入口，独立 ReactFlow 实例 |

> 已有高风险文件见 `08-ui-rules.md`，本表为 v2.0 **新增**部分，两表共同生效。

---

## z-index 层级扩展

在 `08-ui-rules.md` 已有基础（z-0 至 z-[60]）之上，v2.0 新增以下层级：

```
z-[55]  SetupWizardStepBar     向导顶部步骤条（压在 TopNavBar 下方）
z-[58]  AssetCanvasToolbar     资产画布悬浮工具栏（高于步骤条，低于模态）
z-[65]  SetupWizardModal       向导内部确认/错误弹窗（高于现有模态 z-[60]）
z-[70]  ToastContainer         全局 Toast 通知（必须压过所有 UI）
```

**完整层级（含 08 已有）**：

```
z-0    FlowCanvas              画布底层
z-10   CursorOverlay           多人光标层
z-20   LeftToolbar backdrop    左侧工具栏遮罩
z-30   LeftToolbar panel       左侧工具栏面板
z-40   FloatingToolbar         浮动操作栏
z-[45] BottomEditToolbar       底部编辑工具栏
z-50   TopNavBar               顶部导航栏
z-[55] SetupWizardStepBar      向导步骤条（v2.0 新增）
z-[58] AssetCanvasToolbar      资产画布工具栏（v2.0 新增）
z-[60] Modal / Lightbox        模态框 / 大图预览
z-[65] SetupWizardModal        向导弹窗（v2.0 新增）
z-[70] ToastContainer          Toast 通知（v2.0 新增）
```

- ❌ 禁止使用 `z-[999]`、`z-[9999]` 等随意大值
- 新增层时必须更新此表，并与团队沟通层级冲突

---

## 新增节点类型注册规范

v2.0 新增 `MusicNode`、`VideoRemakeNode` 两种节点类型，注册规范如下：

**注册位置**：在 `FlowCanvas` 组件**外部**定义 `nodeTypes`，禁止在组件内部定义（避免每次渲染重建对象导致节点闪烁）。

```typescript
// src/components/canvas/FlowCanvas.tsx

// ✅ 正确：组件外部定义，避免 re-render 时重建
const nodeTypes: Record<string, ComponentType<NodeProps>> = {
  card: CardNode,
  video: VideoNode,
  text: TextNode,
  music: MusicNode,           // v2.0 新增
  video_remake: VideoRemakeNode, // v2.0 新增
};

// ❌ 禁止：组件内部定义
function FlowCanvas() {
  const nodeTypes = { card: CardNode, music: MusicNode }; // ❌ 每次渲染重建
  return <ReactFlow nodeTypes={nodeTypes} />;
}
```

**key 命名规则**：
- 使用 **snake_case**（与 Firestore 节点数据的 `nodeType` 字段保持一致）
- ❌ 禁止 camelCase（`videoRemake`）或 PascalCase（`VideoRemake`）

**类型联合更新**：新增节点类型时，必须同步更新 `src/types/index.ts` 中的 `NodeType` 联合类型：

```typescript
// src/types/index.ts
export type NodeType = 'card' | 'video' | 'text' | 'music' | 'video_remake';
//                                                           ^^v2.0 新增^^
```

---

## 删除操作规范

### 权限校验

删除剧集（series）、剧（episode）及其下属资产时，**必须**校验操作者为创建者：

```typescript
// src/app/api/series/[series_id]/route.ts
async function deleteSeries(seriesId: string, userId: string) {
  const seriesSnap = await getDoc(doc(db, 'series', seriesId));
  if (!seriesSnap.exists()) {
    throw new Error('剧集不存在');
  }
  if (seriesSnap.data().created_by !== userId) {
    throw new Error('只有创建者可以删除剧集');
  }
  // 继续执行删除...
}
```

### 级联硬删除

删除 series 时，**必须**同步删除以下关联数据（使用 `writeBatch`，每批 ≤499 条）：

```
series
  └── episodes（该 series 下所有集）
       └── shot_node_bindings（与各集分镜关联的绑定记录）
  └── series_setup（向导配置文档）
  └── character_variants（人物变体资产）
  └── scene_assets（场景资产）
  └── prop_assets（道具资产）
```

```typescript
async function cascadeDeleteSeries(seriesId: string) {
  // 分批获取并删除所有关联集合
  const collections = [
    query(collection(db, 'episodes'), where('series_id', '==', seriesId)),
    query(collection(db, 'character_variants'), where('series_id', '==', seriesId)),
    query(collection(db, 'scene_assets'), where('series_id', '==', seriesId)),
    query(collection(db, 'prop_assets'), where('series_id', '==', seriesId)),
  ];

  for (const q of collections) {
    const snap = await getDocs(q);
    const chunks = chunkArray(snap.docs, 499); // 分批
    for (const chunk of chunks) {
      const batch = writeBatch(db);
      chunk.forEach(d => batch.delete(d.ref));
      await batch.commit();
    }
  }

  // 最后删除主文档
  await deleteDoc(doc(db, 'series', seriesId));
  await deleteDoc(doc(db, 'series_setup', seriesId));
}
```

- ❌ **禁止软删除**（不得添加 `deleted_at` 字段或 `is_deleted` 标记）
- ❌ 禁止只删除主文档而遗留孤儿子集合数据
- 前端删除前必须展示确认弹窗，显示将被删除的资产数量

---

## 框选分组规范

### 技术实现

v2.0 阶段使用 ReactFlow 内置 **Group Node** 实现框选分组，**不得**自行实现分组逻辑：

```typescript
// ✅ 正确：使用 ReactFlow Group Node
const groupNode: Node = {
  id: `group-${nanoid()}`,
  type: 'group',
  position: { x: boundingBox.x - 20, y: boundingBox.y - 20 },
  style: {
    width: boundingBox.width + 40,
    height: boundingBox.height + 40,
    backgroundColor: 'rgba(99, 102, 241, 0.05)',
    border: '1.5px dashed rgba(99, 102, 241, 0.4)',
    borderRadius: '8px',
  },
  data: { label: '分组' },
};
```


### 操作入口

- 框选多节点后，右键菜单显示\"创建分组\"
- 分组操作入口统一在 `src/components/canvas/ContextMenu.tsx`，**禁止**在其他位置添加入口

---

## 异步任务队列命名规范

v2.0 新增的异步生成任务，Job 名称必须遵守以下格式和表格：

**格式**：`{模块}_{动作}_job`（snake_case，全小写）

| Job 名称 | 触发场景 | 对应 API Route |
|----------|----------|----------------|
| `image_generate_job` | Series Setup 第3步生成人物/场景/道具图片 | `/api/generate/image` |
| `music_generate_job` | MusicNode 触发 TTS/BGM 生成 | `/api/generate/music` |
| `video_remake_job` | VideoRemakeNode 触发重制 | `/api/generate/video-remake` |
| `style_cover_job` | 风格库封面异步生成 | `/api/admin/generate-style-cover` |

**每个 Job Worker 必须实现**：

```typescript
// worker/ 目录下对应 worker 文件
interface JobWorkerConfig {
  maxRetries: number;    // 必须设置，推荐 3
  timeout: number;       // 必须设置，单位 ms，推荐 120_000（2分钟）
  backoff: 'exponential' | 'fixed'; // 推荐 exponential
}

// ✅ 正确示例
const imageGenerateWorker: JobWorkerConfig = {
  maxRetries: 3,
  timeout: 120_000,
  backoff: 'exponential',
};
```

- ❌ 禁止 Job 名称使用 camelCase（`imageGenerateJob`）或 PascalCase
- ❌ 禁止 Worker 缺少 `maxRetries` 或 `timeout` 配置（防止任务永久挂起）
- Job 失败时必须将错误信息回写到对应 Firestore 文档的 `error` 字段，前端据此展示错误状态
