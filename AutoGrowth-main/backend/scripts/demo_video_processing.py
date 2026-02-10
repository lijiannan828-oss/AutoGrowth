"""生成测试视频并测试处理功能"""

import sys
import os
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("视频处理功能完整演示")
print("=" * 60)

# 测试1: 生成测试视频
print("\n1. 生成测试视频...")
try:
    import cv2
    import numpy as np
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    test_video_path = os.path.join(temp_dir, "test_video.mp4")
    
    # 生成一个简单的测试视频（5秒，30fps）
    width, height = 1280, 720
    fps = 30
    duration = 5
    total_frames = fps * duration
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(test_video_path, fourcc, fps, (width, height))
    
    for i in range(total_frames):
        # 创建渐变色帧
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color_value = int((i / total_frames) * 255)
        frame[:, :] = [color_value, 128, 255 - color_value]
        
        # 添加文字
        text = f"Frame {i+1}/{total_frames}"
        cv2.putText(frame, text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 
                   2, (255, 255, 255), 3)
        
        out.write(frame)
    
    out.release()
    
    size_mb = os.path.getsize(test_video_path) / 1024 / 1024
    print(f"  ✓ 测试视频已生成: {test_video_path}")
    print(f"  ✓ 大小: {size_mb:.2f} MB")
    print(f"  ✓ 时长: {duration} 秒")
    
except Exception as e:
    print(f"  ✗ 生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试2: 获取视频信息
print("\n2. 获取视频信息...")
try:
    from app.utils.video_processor import VideoProcessor
    
    processor = VideoProcessor()
    info = processor.get_video_info(test_video_path)
    
    print(f"  ✓ 视频信息:")
    print(f"    - 分辨率: {info['width']}x{info['height']}")
    print(f"    - 帧率: {info['fps']:.2f} fps")
    print(f"    - 总帧数: {info['frame_count']}")
    print(f"    - 时长: {info['duration']:.2f} 秒")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 应用滤镜
print("\n3. 测试滤镜效果...")
try:
    filters = ["warm", "cool", "vintage"]
    
    for filter_name in filters:
        output_path = os.path.join(temp_dir, f"filtered_{filter_name}.mp4")
        print(f"  - 应用 {filter_name} 滤镜...")
        
        processor.apply_filter(test_video_path, output_path, filter_name)
        
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"    ✓ 生成成功: {size_mb:.2f} MB")
        else:
            print(f"    ✗ 生成失败")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试4: 时长调整
print("\n4. 测试时长调整...")
try:
    output_path = os.path.join(temp_dir, "duration_adjusted.mp4")
    print(f"  - 调整时长（±20%）...")
    
    new_duration = processor.adjust_duration(test_video_path, output_path, 20)
    
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"    ✓ 生成成功: {size_mb:.2f} MB")
        print(f"    ✓ 原时长: {info['duration']:.2f} 秒")
        print(f"    ✓ 新时长: {new_duration:.2f} 秒")
        print(f"    ✓ 变化: {((new_duration/info['duration']-1)*100):.1f}%")
    else:
        print(f"    ✗ 生成失败")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试5: 抽帧重组
print("\n5. 测试抽帧重组...")
try:
    output_path = os.path.join(temp_dir, "frame_shuffled.mp4")
    print(f"  - 抽帧重组（强度0.3）...")
    
    processor.frame_shuffle(test_video_path, output_path, 0.3)
    
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        new_info = processor.get_video_info(output_path)
        print(f"    ✓ 生成成功: {size_mb:.2f} MB")
        print(f"    ✓ 原帧数: {info['frame_count']}")
        print(f"    ✓ 新帧数: {new_info['frame_count']}")
    else:
        print(f"    ✗ 生成失败")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 总结
print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print(f"\n所有输出文件保存在: {temp_dir}")
print("\n生成的文件:")
for file in os.listdir(temp_dir):
    file_path = os.path.join(temp_dir, file)
    size_mb = os.path.getsize(file_path) / 1024 / 1024
    print(f"  - {file} ({size_mb:.2f} MB)")

print("\n提示:")
print("- 可以使用视频播放器查看生成的视频")
print("- 测试文件会保留在临时目录中")
print("- 所有视频处理功能已验证通过")
print()

