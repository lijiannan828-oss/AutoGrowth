# 贴纸素材目录

## 📁 目录结构

```
stickers/
├── emoji/          # 表情类贴纸
│   ├── fire.png
│   ├── heart.png
│   ├── laugh.png
│   ├── love.png
│   ├── cool.png
│   ├── cry.png
│   ├── shock.png
│   └── party.png
├── gesture/        # 手势类贴纸
│   ├── thumbsup.png
│   ├── clap.png
│   └── muscle.png
├── decoration/     # 装饰类贴纸
│   ├── star.png
│   ├── sparkle.png
│   ├── crown.png
│   └── diamond.png
└── text/          # 文字标签贴纸
    ├── hot.png
    ├── new.png
    └── sale.png
```

## 🎨 贴纸规格要求

- **格式**: PNG (必须支持透明背景)
- **尺寸**: 512x512 px (推荐)
- **文件大小**: < 500KB
- **背景**: 透明

## 📥 如何获取贴纸

### 方法 1: 从 Flaticon 下载 (推荐)

1. 访问 https://www.flaticon.com/
2. 搜索 "3D emoji fire" 或 "3D sticker heart"
3. 选择喜欢的图标
4. 点击 "Download PNG"
5. 选择 512px 尺寸
6. 保存到对应目录

### 方法 2: 使用 Freepik

1. 访问 https://www.freepik.com/
2. 搜索 "3D emoji sticker"
3. 下载 PNG 格式
4. 使用 Remove.bg 去除背景（如果需要）

### 方法 3: 使用 AI 生成

使用 DALL-E 或 Midjourney 生成：
```
Prompt: "3D cute emoji sticker, fire emoji, transparent background, PNG, high quality"
```

## 🔧 图片优化

下载后使用 TinyPNG 压缩：
- 访问 https://tinypng.com/
- 上传 PNG 图片
- 下载压缩后的版本

## 📝 使用示例

在视频裂变任务中使用：

```json
{
  "transforms": [
    {
      "type": "sticker",
      "sticker_id": "sticker_fire",
      "position": "top_right"
    }
  ]
}
```

## 🎯 推荐的免费贴纸资源

1. **Flaticon** - https://www.flaticon.com/
2. **Freepik** - https://www.freepik.com/
3. **IconScout** - https://iconscout.com/
4. **Emoji Kitchen** - https://emojikitchen.dev/
5. **3D Icons** - https://3dicons.co/

## ⚠️ 注意事项

- 确保图片有透明背景
- 文件名使用小写字母和下划线
- 避免使用特殊字符
- 定期清理未使用的贴纸

