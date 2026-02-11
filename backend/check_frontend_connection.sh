#!/bin/bash

echo "=========================================="
echo "前端连接诊断脚本"
echo "=========================================="
echo ""

# 检查后端服务
echo "1. 检查后端服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务运行中 (http://localhost:8000)"
else
    echo "   ❌ 后端服务未运行"
    exit 1
fi

# 检查前端服务
echo ""
echo "2. 检查前端服务..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ 前端服务运行中 (http://localhost:3000)"
else
    echo "   ❌ 前端服务未运行"
    exit 1
fi

# 测试后端API
echo ""
echo "3. 测试后端API..."
API_RESPONSE=$(curl -s 'http://localhost:8000/api/data/programs?page=1&page_size=5')
if [ $? -eq 0 ]; then
    TOTAL=$(echo "$API_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('total', 0))" 2>/dev/null)
    ITEMS_COUNT=$(echo "$API_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('items', [])))" 2>/dev/null)
    echo "   ✅ API 响应正常"
    echo "   📊 总记录数: $TOTAL"
    echo "   📊 当前页记录数: $ITEMS_COUNT"
else
    echo "   ❌ API 请求失败"
    exit 1
fi

# 检查CORS
echo ""
echo "4. 检查CORS配置..."
CORS_HEADER=$(curl -s -I -H "Origin: http://localhost:3000" 'http://localhost:8000/api/data/programs?page=1&page_size=5' | grep -i "access-control-allow-origin")
if [ -n "$CORS_HEADER" ]; then
    echo "   ✅ CORS 配置正常"
    echo "   $CORS_HEADER"
else
    echo "   ⚠️  CORS 头未找到"
fi

# 检查环境变量
echo ""
echo "5. 检查前端环境变量..."
if [ -f "../frontend/.env.local" ]; then
    echo "   ✅ .env.local 文件存在"
    grep "NEXT_PUBLIC_API_URL" ../frontend/.env.local || echo "   ⚠️  NEXT_PUBLIC_API_URL 未设置"
elif [ -f "../frontend/.env" ]; then
    echo "   ✅ .env 文件存在"
    grep "NEXT_PUBLIC_API_URL" ../frontend/.env || echo "   ⚠️  NEXT_PUBLIC_API_URL 未设置"
else
    echo "   ⚠️  环境变量文件不存在"
fi

echo ""
echo "=========================================="
echo "诊断完成"
echo "=========================================="
echo ""
echo "下一步排查："
echo "1. 打开浏览器开发者工具 (F12)"
echo "2. 查看 Console 标签，检查是否有错误"
echo "3. 查看 Network 标签，检查 /api/data/programs 请求"
echo "4. 检查请求状态码和响应数据"
echo ""

