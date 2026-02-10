#!/bin/bash
# Script to create Firestore indexes
# This script uses gcloud CLI to create indexes from firestore.indexes.json

set -e

PROJECT_ID="fleet-blend-469520-n7"
INDEXES_FILE="firestore.indexes.json"

echo "================================================================================"
echo "  Firestore 索引创建脚本"
echo "================================================================================"
echo ""
echo "项目 ID: ${PROJECT_ID}"
echo "索引文件: ${INDEXES_FILE}"
echo ""

# Check if firestore.indexes.json exists
if [ ! -f "${INDEXES_FILE}" ]; then
    echo "❌ 错误: 索引文件 ${INDEXES_FILE} 不存在"
    echo "   请确保在项目根目录运行此脚本"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ 错误: gcloud CLI 未安装"
    echo "   请安装 Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ 错误: 未登录到 gcloud"
    echo "   请运行: gcloud auth login"
    exit 1
fi

echo "📋 索引配置预览:"
echo ""
cat "${INDEXES_FILE}" | python3 -m json.tool | head -30
echo ""
echo "..."
echo ""

# Confirm
read -p "是否继续创建索引? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 1
fi

echo ""
echo "🚀 开始创建索引..."
echo ""

# Deploy indexes using Firebase CLI (if available) or gcloud
if command -v firebase &> /dev/null; then
    echo "使用 Firebase CLI 部署索引..."
    firebase deploy --only firestore:indexes --project "${PROJECT_ID}"
else
    echo "⚠️  Firebase CLI 未安装，使用 gcloud 手动创建..."
    echo ""
    echo "请按照以下步骤手动创建索引:"
    echo ""
    echo "1. 打开 Firebase Console:"
    echo "   https://console.firebase.google.com/project/${PROJECT_ID}/firestore/indexes"
    echo ""
    echo "2. 点击 '创建索引'"
    echo ""
    echo "3. 根据 ${INDEXES_FILE} 中的配置创建以下索引:"
    echo ""
    
    # Parse and display indexes
    python3 << 'EOF'
import json
import sys

try:
    with open('firestore.indexes.json', 'r') as f:
        data = json.load(f)
    
    indexes = data.get('indexes', [])
    print(f"共 {len(indexes)} 个索引需要创建:\n")
    
    for i, idx in enumerate(indexes, 1):
        collection = idx.get('collectionGroup', 'N/A')
        fields = idx.get('fields', [])
        
        print(f"{i}. Collection: {collection}")
        print("   Fields:")
        for field in fields:
            field_path = field.get('fieldPath', 'N/A')
            order = field.get('order', 'ASCENDING')
            print(f"     - {field_path} ({order})")
        print()
        
except Exception as e:
    print(f"❌ 解析索引文件失败: {e}")
    sys.exit(1)
EOF
    
    echo ""
    echo "或者，您可以安装 Firebase CLI 后运行:"
    echo "  npm install -g firebase-tools"
    echo "  firebase login"
    echo "  firebase deploy --only firestore:indexes --project ${PROJECT_ID}"
fi

echo ""
echo "================================================================================"
echo "  索引创建完成"
echo "================================================================================"
echo ""
echo "⚠️  注意: 索引创建可能需要几分钟时间"
echo "   您可以在 Firebase Console 中查看索引状态:"
echo "   https://console.firebase.google.com/project/${PROJECT_ID}/firestore/indexes"
echo ""
echo "   索引状态为 'Enabled' 时即可使用"
echo ""


