"""Storyline template system for video fission."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class StorylineType(str, Enum):
    """故事线类型"""
    ROMANCE = "romance"  # 言情
    REVENGE = "revenge"  # 复仇
    REBIRTH = "rebirth"  # 重生
    COUNTERATTACK = "counterattack"  # 逆袭
    SUSPENSE = "suspense"  # 悬疑
    COMEDY = "comedy"  # 喜剧


@dataclass
class SceneSegment:
    """场景片段"""
    start_frame: int
    end_frame: int
    scene_type: str  # 场景类型：对话、动作、情感、转场等
    importance: float  # 重要性评分 0-1
    emotion: str  # 情感标签：happy, sad, angry, surprise等


@dataclass
class StorylineTemplate:
    """故事线模板"""
    template_id: str
    name: str
    storyline_type: StorylineType
    description: str
    scene_structure: List[Dict[str, Any]]  # 场景结构定义
    key_moments: List[int]  # 关键时刻的帧位置（百分比）
    transition_rules: Dict[str, Any]  # 转场规则


class StorylineEngine:
    """故事线重组引擎"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, StorylineTemplate]:
        """加载预定义的故事线模板"""
        templates = {}
        
        # 言情模板
        templates["romance_classic"] = StorylineTemplate(
            template_id="romance_classic",
            name="经典言情",
            storyline_type=StorylineType.ROMANCE,
            description="相遇-误会-和解-甜蜜",
            scene_structure=[
                {"type": "meet", "weight": 0.15, "emotion": "surprise"},
                {"type": "conflict", "weight": 0.25, "emotion": "angry"},
                {"type": "misunderstanding", "weight": 0.20, "emotion": "sad"},
                {"type": "resolution", "weight": 0.20, "emotion": "happy"},
                {"type": "sweet", "weight": 0.20, "emotion": "happy"},
            ],
            key_moments=[10, 35, 60, 85],  # 百分比位置
            transition_rules={"fade_duration": 0.5, "style": "smooth"}
        )
        
        # 复仇模板
        templates["revenge_intense"] = StorylineTemplate(
            template_id="revenge_intense",
            name="激烈复仇",
            storyline_type=StorylineType.REVENGE,
            description="受辱-隐忍-爆发-复仇",
            scene_structure=[
                {"type": "humiliation", "weight": 0.20, "emotion": "sad"},
                {"type": "planning", "weight": 0.15, "emotion": "angry"},
                {"type": "preparation", "weight": 0.15, "emotion": "determined"},
                {"type": "confrontation", "weight": 0.30, "emotion": "angry"},
                {"type": "victory", "weight": 0.20, "emotion": "satisfied"},
            ],
            key_moments=[15, 30, 55, 90],
            transition_rules={"fade_duration": 0.3, "style": "sharp"}
        )
        
        # 重生模板
        templates["rebirth_redemption"] = StorylineTemplate(
            template_id="rebirth_redemption",
            name="重生救赎",
            storyline_type=StorylineType.REBIRTH,
            description="前世悲剧-重生-改变-圆满",
            scene_structure=[
                {"type": "past_tragedy", "weight": 0.15, "emotion": "sad"},
                {"type": "rebirth", "weight": 0.10, "emotion": "surprise"},
                {"type": "realization", "weight": 0.15, "emotion": "determined"},
                {"type": "change_fate", "weight": 0.35, "emotion": "hopeful"},
                {"type": "happy_ending", "weight": 0.25, "emotion": "happy"},
            ],
            key_moments=[8, 25, 50, 85],
            transition_rules={"fade_duration": 0.8, "style": "dreamy"}
        )
        
        # 逆袭模板
        templates["counterattack_rise"] = StorylineTemplate(
            template_id="counterattack_rise",
            name="逆袭崛起",
            storyline_type=StorylineType.COUNTERATTACK,
            description="低谷-觉醒-奋斗-成功",
            scene_structure=[
                {"type": "low_point", "weight": 0.20, "emotion": "sad"},
                {"type": "awakening", "weight": 0.15, "emotion": "determined"},
                {"type": "struggle", "weight": 0.30, "emotion": "hopeful"},
                {"type": "breakthrough", "weight": 0.20, "emotion": "excited"},
                {"type": "success", "weight": 0.15, "emotion": "happy"},
            ],
            key_moments=[12, 30, 60, 88],
            transition_rules={"fade_duration": 0.4, "style": "energetic"}
        )
        
        return templates

    def analyze_video_scenes(self, video_info: Dict[str, Any]) -> List[SceneSegment]:
        """分析视频场景（简化版，实际应使用AI模型）"""
        total_frames = video_info["frame_count"]
        fps = video_info["fps"]
        
        # 简单分段：将视频分成若干段
        num_segments = 10
        segment_length = total_frames // num_segments
        
        segments = []
        scene_types = ["dialogue", "action", "emotion", "transition"]
        emotions = ["happy", "sad", "angry", "surprise", "neutral"]
        
        for i in range(num_segments):
            start = i * segment_length
            end = min((i + 1) * segment_length, total_frames)
            
            segments.append(SceneSegment(
                start_frame=start,
                end_frame=end,
                scene_type=scene_types[i % len(scene_types)],
                importance=0.5 + (i % 3) * 0.2,  # 简单的重要性评分
                emotion=emotions[i % len(emotions)]
            ))
        
        return segments

    def reconstruct_storyline(
        self,
        segments: List[SceneSegment],
        template: StorylineTemplate,
        target_duration_ratio: float = 1.0
    ) -> List[Dict[str, Any]]:
        """根据模板重组故事线"""
        reconstructed = []
        total_frames = sum(seg.end_frame - seg.start_frame for seg in segments)
        target_frames = int(total_frames * target_duration_ratio)
        
        # 按照模板的场景结构分配帧数
        for scene_def in template.scene_structure:
            scene_frames = int(target_frames * scene_def["weight"])
            
            # 找到匹配的片段
            matching_segments = [
                seg for seg in segments
                if seg.emotion == scene_def["emotion"] or seg.importance > 0.6
            ]
            
            if not matching_segments:
                matching_segments = segments[:len(segments)//2]
            
            # 选择片段
            selected = matching_segments[0] if matching_segments else segments[0]
            
            reconstructed.append({
                "start_frame": selected.start_frame,
                "end_frame": min(selected.start_frame + scene_frames, selected.end_frame),
                "scene_type": scene_def["type"],
                "emotion": scene_def["emotion"],
                "transition": template.transition_rules
            })
        
        return reconstructed

    def get_template(self, template_id: str) -> Optional[StorylineTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)

    def list_templates(self, storyline_type: Optional[StorylineType] = None) -> List[StorylineTemplate]:
        """列出所有模板"""
        templates = list(self.templates.values())
        if storyline_type:
            templates = [t for t in templates if t.storyline_type == storyline_type]
        return templates

