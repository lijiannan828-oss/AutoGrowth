# 项目概述

## 🌐 语言规范

- **永远使用中文**进行所有交流和文档编写

---

## 📋 项目简介

CineFlow 是一个 AI 驱动的视频创作工作流平台，支持图片生成、视频生成、多人协作等功能。

### 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 14 (App Router) |
| 前端 | React 18 + TypeScript |
| 样式 | Tailwind CSS |
| 动画 | Framer Motion |
| 状态管理 | Zustand |
| 画布 | ReactFlow |
| 数据库 | Firebase Firestore |
| 存储 | Firebase Storage |
| 认证 | Firebase Auth |
| 协作 | Yjs + WebSocket |

---

## 📁 目录结构

```
cineflow-mvp/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── api/                # API Routes
│   │   │   ├── generate/       # 生成相关 API
│   │   │   ├── upload/         # 上传相关 API
│   │   │   └── queue/          # 队列相关 API
│   │   ├── canvas/             # 画布页面
│   │   └── login/              # 登录页面
│   │
│   ├── components/             # React 组件
│   │   ├── canvas/             # 画布相关组件
│   │   ├── nodes/              # 节点组件
│   │   ├── storyboard/         # 分镜表组件
│   │   └── toolbar/            # 工具栏组件
│   │
│   ├── lib/                    # 工具库
│   │   ├── firebase/           # Firebase 服务
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── store/              # Zustand Store
│   │   ├── api/                # API 客户端
│   │   └── collaboration/      # 协作相关
│   │
│   ├── config/                 # 配置文件
│   └── types/                  # TypeScript 类型
│
├── server/                     # WebSocket 服务器
└── worker/                     # 队列 Worker
```

---

## 🔧 常用命令

```bash
# 开发
npm run dev              # 启动开发服务器
npm run dev:lan          # 局域网模式启动

# 构建
npm run build            # 生产构建
npm run start            # 启动生产服务器

# WebSocket
npm run websocket        # 启动 WebSocket 服务器

# 检查
npm run lint             # ESLint 检查
```
