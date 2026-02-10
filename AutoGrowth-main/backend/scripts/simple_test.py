"""简单的本地测试 - 测试核心功能"""

print("=" * 60)
print("AI 裂变素材生成系统 - 简单测试")
print("=" * 60)

# 测试1: 导入检查
print("\n1. 检查依赖...")
try:
    import cv2
    print("  ✓ OpenCV")
except:
    print("  ✗ OpenCV 未安装")

try:
    import numpy
    print("  ✓ NumPy")
except:
    print("  ✗ NumPy 未安装")

# 测试2: 导入故事线引擎
print("\n2. 测试故事线引擎...")
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from app.utils.storyline_engine import StorylineEngine
    
    engine = StorylineEngine()
    templates = engine.list_templates()
    
    print(f"  ✓ 加载了 {len(templates)} 个模板:")
    for t in templates:
        print(f"    - {t.name}")
    
    # 测试场景分析
    video_info = {
        "frame_count": 900,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "duration": 30.0
    }
    
    segments = engine.analyze_video_scenes(video_info)
    print(f"\n  ✓ 场景分析: {len(segments)} 个片段")
    
    # 测试重组
    template = templates[0]
    reconstructed = engine.reconstruct_storyline(segments, template)
    print(f"  ✓ 故事线重组: {len(reconstructed)} 个场景")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 检查FFmpeg
print("\n3. 检查FFmpeg...")
try:
    import subprocess
    result = subprocess.run(['ffmpeg', '-version'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("  ✓ FFmpeg 已安装")
    else:
        print("  ✗ FFmpeg 未正确安装")
except:
    print("  ✗ FFmpeg 未安装")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)

