#!/bin/bash
# 检查 GDrive 路径的脚本

echo "================================================================================"
echo "检查 GDrive 路径"
echo "================================================================================"
echo ""

echo "1. 检查 GDrive 根目录:"
rclone lsd "my-drive:" 2>&1 | head -20
echo ""

echo "2. 尝试不同的路径格式:"
echo "   格式1: US Programs/US044P01S01_Runaway Prince's Secret Vacation"
rclone lsd "my-drive:US Programs/US044P01S01_Runaway Prince's Secret Vacation" 2>&1 | head -5
echo ""

echo "   格式2: 'US Programs/US044P01S01_Runaway Prince'\''s Secret Vacation'"
rclone lsd "my-drive:US Programs/US044P01S01_Runaway Prince's Secret Vacation" 2>&1 | head -5
echo ""

echo "3. 列出所有顶级目录:"
rclone lsd "my-drive:" 2>&1 | head -30
echo ""

echo "4. 检查是否有共享文件夹:"
rclone backend drives "my-drive:" 2>&1 | head -10
echo ""

echo "================================================================================"
echo "请提供以下信息："
echo "1. GDrive 中的实际路径格式是什么？"
echo "2. 这个文件夹是在根目录下还是在某个共享文件夹中？"
echo "3. 能否提供实际的文件夹 ID 或完整路径？"
echo "================================================================================"

