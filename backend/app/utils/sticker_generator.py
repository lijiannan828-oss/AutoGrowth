"""贴纸管理器 - 使用GCS存储的现成贴纸PNG或FFmpeg内置绘图"""

from typing import Dict, List

# 贴纸位置配置 - 放在角落，不遮挡画面和字幕
# 使用FFmpeg overlay滤镜的坐标表达式
STICKER_POSITIONS = {
    "top_left": {"x": "20", "y": "20", "name": "左上角", "css": "top: 5%; left: 5%;"},
    "top_right": {"x": "main_w-overlay_w-20", "y": "20", "name": "右上角", "css": "top: 5%; right: 5%;"},
    "bottom_left": {"x": "20", "y": "main_h-overlay_h-150", "name": "左下角", "css": "bottom: 15%; left: 5%;"},
    "bottom_right": {"x": "main_w-overlay_w-20", "y": "main_h-overlay_h-150", "name": "右下角", "css": "bottom: 15%; right: 5%;"},
}

# 贴纸库 - 使用FFmpeg drawtext绘制文字贴纸
STICKER_CATALOG = {
    # 表情类 - 使用emoji字符
    "emoji_heart": {"name": "爱心", "text": "❤️", "color": "red", "bg": "#FF6B6B"},
    "emoji_star": {"name": "星星", "text": "⭐", "color": "yellow", "bg": "#FFD93D"},
    "emoji_fire": {"name": "火焰", "text": "🔥", "color": "orange", "bg": "#FF8C00"},
    "emoji_thumbsup": {"name": "点赞", "text": "👍", "color": "blue", "bg": "#4ECDC4"},
    "emoji_sparkle": {"name": "闪耀", "text": "✨", "color": "gold", "bg": "#FFD700"},
    "emoji_crown": {"name": "皇冠", "text": "👑", "color": "gold", "bg": "#FFD700"},
    "emoji_diamond": {"name": "钻石", "text": "💎", "color": "cyan", "bg": "#00CED1"},
    "emoji_rocket": {"name": "火箭", "text": "�", "color": "red", "bg": "#FF6347"},
    "emoji_gift": {"name": "礼物", "text": "🎁", "color": "red", "bg": "#E74C3C"},
    "emoji_music": {"name": "音乐", "text": "🎵", "color": "purple", "bg": "#9B59B6"},

    # 文字标签类
    "tag_hot": {"name": "HOT", "text": "HOT", "color": "white", "bg": "#FF4757"},
    "tag_new": {"name": "NEW", "text": "NEW", "color": "white", "bg": "#2ED573"},
    "tag_top": {"name": "TOP", "text": "TOP", "color": "white", "bg": "#FFA502"},
    "tag_vip": {"name": "VIP", "text": "VIP", "color": "white", "bg": "#9B59B6"},
    "tag_best": {"name": "BEST", "text": "BEST", "color": "white", "bg": "#3498DB"},
    "tag_like": {"name": "LIKE", "text": "LIKE", "color": "white", "bg": "#E91E63"},
}


def get_sticker_list() -> List[Dict]:
    """获取所有可用贴纸列表"""
    return [
        {"id": k, "name": v["name"], "text": v["text"], "bg": v["bg"]}
        for k, v in STICKER_CATALOG.items()
    ]


def get_position_list() -> List[Dict]:
    """获取所有可用位置列表"""
    return [
        {"id": k, "name": v["name"], "css": v["css"]}
        for k, v in STICKER_POSITIONS.items()
    ]


def get_sticker_ffmpeg_filter(sticker_id: str, position: str, size: int = 80) -> str:
    """
    生成FFmpeg滤镜字符串，用于在视频上绘制贴纸
    使用drawbox + drawtext组合实现
    """
    sticker = STICKER_CATALOG.get(sticker_id)
    pos = STICKER_POSITIONS.get(position)

    if not sticker or not pos:
        return ""

    text = sticker["text"]
    bg_color = sticker["bg"]
    text_color = sticker["color"]

    # 计算位置
    x_expr = pos["x"]
    y_expr = pos["y"]

    # 对于文字标签，使用drawtext
    if sticker_id.startswith("tag_"):
        # 绘制背景框 + 文字
        filter_str = (
            f"drawbox=x={x_expr}:y={y_expr}:w={size}:h={size//2}:color={bg_color}@0.8:t=fill,"
            f"drawtext=text='{text}':fontsize={size//3}:fontcolor={text_color}:"
            f"x={x_expr}+{size//4}:y={y_expr}+{size//6}"
        )
    else:
        # 对于emoji，直接绘制文字（需要支持emoji的字体）
        filter_str = (
            f"drawtext=text='{text}':fontsize={size}:"
            f"x={x_expr}:y={y_expr}"
        )

    return filter_str

