# UI 开发限制规则

> **更新日期**：2026-02-10

---

## z-index 层级规范

新增 UI 层时，**必须**遵守以下层级并在此登记，**禁止**随意使用 z-[999] 等临时值。

```
z-0    FlowCanvas          画布底层
z-10   CursorOverlay       多人光标层
z-20   LeftToolbar backdrop 左侧工具栏遮罩
z-30   LeftToolbar panel    左侧工具栏面板
z-40   FloatingToolbar      浮动操作栏
z-[45] BottomEditToolbar    底部编辑工具栏
z-50   TopNavBar            顶部导航栏
z-[60] Modal / Lightbox     模态框 / 大图预览
```

---

## 高风险文件（修改前必须与团队沟通）

以下文件逻辑密集、多人同时修改极易冲突，**禁止**未经沟通直接修改：

| 文件 | 行数 | 原因 |
|------|------|------|
| `src/app/canvas/page.tsx` | 2,608 | 画布主入口，逻辑最密集 |
| `src/components/panels/GenerationPanel.tsx` | 1,005 | AI 生成核心，参数逻辑复杂 |
| `src/components/panels/GenerationPanelPro.tsx` | 850 | 与 GenerationPanel 强耦合 |
| `src/components/toolbar/UnifiedAssetLibrary.tsx` | 843 | 旧版资产库，正在迁移 |
| `src/components/toolbar/PersonalAssets.tsx` | 784 | 与 Firebase 深度绑定 |
| `src/components/ui/sidebar.tsx` | 773 | 基础组件，改动影响全局 |
| `src/components/nodes/CardNode.tsx` | 733 | 含生成/编辑/预览逻辑 |
| `src/components/toolbar/TeamSpace.tsx` | 715 | 协作逻辑复杂 |
| `src/components/nodes/VideoNode.tsx` | 691 | 含播放控制 |
| `src/components/storyboard/StoryboardTable.tsx` | 673 | 表格逻辑复杂 |
