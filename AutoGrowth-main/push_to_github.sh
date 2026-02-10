#!/bin/bash

# 推送到 GitHub 脚本

echo "🚀 AutoGrowth 部署推送脚本"
echo "================================"
echo ""

# 检查远程仓库
echo "📋 当前远程仓库配置:"
git remote -v
echo ""

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  检测到未提交的更改，请先提交"
    git status --short
    exit 1
fi

echo "✅ 代码已准备就绪"
echo ""

# 选择推送方式
echo "请选择推送方式:"
echo "1) HTTPS + Personal Access Token (推荐)"
echo "2) SSH"
read -p "请输入选项 (1 或 2): " choice

case $choice in
    1)
        echo ""
        echo "使用 HTTPS 方式推送..."
        echo "提示: 如果提示输入密码，请输入你的 GitHub Personal Access Token"
        echo ""
        git push -u origin main
        ;;
    2)
        echo ""
        echo "切换到 SSH 方式..."
        git remote set-url origin git@github.com:lijiannan828/AutoGrowth.git
        echo ""
        echo "使用 SSH 方式推送..."
        git push -u origin main
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo ""
    echo "📊 监控部署:"
    echo "   https://github.com/lijiannan828/AutoGrowth/actions"
    echo ""
    echo "⏱️  部署时间: 约 5-10 分钟"
else
    echo ""
    echo "❌ 推送失败"
    echo ""
    echo "可能的原因:"
    echo "1. 仓库不存在或名称不正确"
    echo "2. 没有访问权限"
    echo "3. 认证失败"
    echo ""
    echo "请检查:"
    echo "- 仓库是否存在: https://github.com/lijiannan828/AutoGrowth"
    echo "- Personal Access Token 是否有效（如果使用 HTTPS）"
    echo "- SSH 密钥是否已添加到 GitHub（如果使用 SSH）"
fi






