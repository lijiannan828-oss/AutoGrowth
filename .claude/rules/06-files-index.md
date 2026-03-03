# 关键文件索引

## 配置文件

| 文件 | 说明 |
|------|------|
| `src/config/features.ts` | 功能开关配置 |
| `src/lib/firebase/config.ts` | Firebase 配置 |
| `.env.local` | 环境变量（本地） |

---

## API Routes

| 文件 | 说明 |
|------|------|
| `src/app/api/generate/image/route.ts` | 图片生成 API |
| `src/app/api/generate/video/route.ts` | 视频生成 API |
| `src/app/api/upload/image/route.ts` | 图片上传 API |

---

## 状态管理

| 文件 | 说明 |
|------|------|
| `src/lib/store/generation-store.ts` | 生成任务状态 |
| `src/lib/store/storyboard-store.ts` | 分镜表状态 |

---

## Firebase 服务

| 文件 | 说明 |
|------|------|
| `src/lib/firebase/personal-assets.ts` | 个人资产 CRUD |
| `src/lib/firebase/shared-assets.ts` | 共享资产 CRUD |
| `src/lib/firebase/storage.ts` | 文件存储 |

---

## 核心组件

| 文件 | 说明 |
|------|------|
| `src/components/nodes/CardNode.tsx` | 图片节点组件 |
| `src/components/nodes/VideoNode.tsx` | 视频节点组件 |
| `src/components/canvas/FlowCanvas.tsx` | 画布组件 |

---

## 类型定义

| 文件 | 说明 |
|------|------|
| `src/types/index.ts` | 通用类型 |
| `src/types/generation.ts` | 生成相关类型 |
