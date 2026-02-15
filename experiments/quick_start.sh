#!/bin/bash

# 知识图谱独立评估框架 - 快速开始脚本

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     知识图谱独立评估框架 - 快速开始                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查Python环境
echo "[1/5] 检查Python环境..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python版本: $python_version"
echo ""

# 检查依赖
echo "[2/5] 检查依赖..."
python3 -c "import networkx; print('✓ networkx OK')" || { echo "✗ 缺少networkx"; exit 1; }
python3 -c "import numpy; print('✓ numpy OK')" || { echo "✗ 缺少numpy"; exit 1; }
python3 -c "import pydantic; print('✓ pydantic OK')" || { echo "✗ 缺少pydantic"; exit 1; }
echo ""

# 准备示例数据目录
echo "[3/5] 准备示例数据..."
mkdir -p test_data/com.example.shopping
cp sample_ground_truth.json test_data/com.example.shopping/paths.json
echo "✓ 示例数据已准备到 test_data/com.example.shopping/paths.json"
echo ""

# 显示Ground Truth数据
echo "[4/5] Ground Truth数据概览..."
python3 << 'EOF'
import json
with open('sample_ground_truth.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stats = data.get('statistics', {})
print(f"├─ 应用: {data.get('app_name')}")
print(f"├─ 总路径数: {stats.get('total_paths', 0)}")
print(f"├─ 短路径 (≤5步): {stats.get('short_paths', 0)}")
print(f"├─ 中等路径 (6-10步): {stats.get('medium_paths', 0)}")
print(f"├─ 长路径 (11+步): {stats.get('long_paths', 0)}")
print(f"├─ 总操作数: {stats.get('total_operations', 0)}")
print(f"└─ 平均路径长度: {stats.get('average_path_length', 0):.1f}步")
EOF
echo ""

# 运行评估
echo "[5/5] 运行评估框架..."
echo "执行命令: python3 standalone_evaluation.py --hmtest-dir test_data"
python3 standalone_evaluation.py --hmtest-dir test_data

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   评估完成！                                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 结果文件:"
echo "  - evaluation_results.json  : 详细结果 (JSON格式)"
echo "  - evaluation.log           : 执行日志"
echo ""
echo "📈 查看结果:"
echo "  cat evaluation_results.json | python3 -m json.tool"
echo ""
echo "📝 下一步:"
echo "  1. 使用真实的HmTest数据集替换示例数据"
echo "  2. 运行: python3 standalone_evaluation.py --hmtest-dir /path/to/hmtest/data/apps"
echo "  3. 分析结果，优化系统"
echo ""
