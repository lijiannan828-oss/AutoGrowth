"""快速视频处理测试 - 10秒测试视频"""

import sys
import os
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("快速视频处理测试（10秒视频）")
print("=" * 60)

# 生成10秒测试视频
print("\n1. 生成10秒测试视频...")
try:
    import cv2
    import numpy as np
    
    temp_dir = tempfile.mkdtemp()
    test_video_path = os.path.join(temp_dir, "test_10s.mp4")
    
    width, height = 1280, 720
    fps = 30
    duration = 10  # 10秒
    total_frames = fps * duration
    
    # 先用OpenCV生成临时视频
    temp_video = os.path.join(temp_dir, "temp.avi")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color_value = int((i / total_frames) * 255)
        frame[:, :] = [color_value, 128, 255 - color_value]

        text = f"Frame {i+1}/{total_frames}"
        cv2.putText(frame, text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                   2, (255, 255, 255), 3)
        out.write(frame)

    out.release()

    # 用FFmpeg转换为标准MP4（添加静音音频）
    import subprocess
    cmd = [
        "ffmpeg", "-i", temp_video,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        "-y", test_video_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(temp_video)  # 删除临时文件
    
    size_mb = os.path.getsize(test_video_path) / 1024 / 1024
    print(f"  ✓ 测试视频: {test_video_path}")
    print(f"  ✓ 大小: {size_mb:.2f} MB")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    sys.exit(1)

# 测试滤镜
print("\n2. 测试滤镜（warm）...")
try:
    from app.utils.video_processor import VideoProcessor
    
    processor = VideoProcessor()
    output_path = os.path.join(temp_dir, "filtered_warm.mp4")
    
    processor.apply_filter(test_video_path, output_path, "warm")
    
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"  ✓ 生成成功: {size_mb:.2f} MB")
        print(f"  ✓ 文件: {output_path}")
    else:
        print(f"  ✗ 生成失败")
    
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print(f"\n输出目录: {temp_dir}")
print("\n生成的文件:")
for file in os.listdir(temp_dir):
    file_path = os.path.join(temp_dir, file)
    size_mb = os.path.getsize(file_path) / 1024 / 1024
    print(f"  - {file} ({size_mb:.2f} MB)")

print("\n提示:")
print("- 使用VLC或其他播放器打开视频文件")
print("- 如果能正常播放，说明视频处理功能正常")
print()

