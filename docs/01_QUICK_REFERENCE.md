# 🎯 快速参考卡

**项目**: 鸿蒙App自动化测试知识图谱
**目标**: 路径成功率≥70%, 步骤效率≥60%
**现状**: ✅ 评估系统就绪，合成数据已生成

---

## ⚡ 30秒快速启动

```bash
# 进入项目目录
cd /Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph

# 运行评估
python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data

# 查看结果
cat evaluation_results.json
```

---

## 📊 数据集一览

| 应用 | 路径数 | 短 | 中 | 长 |
|------|--------|----|----|-----|
| 电商 | 12 | 10 | 1 | 1 |
| 社交 | 8 | 5 | 2 | 1 |
| 地图 | 4 | 3 | 1 | 0 |
| 视频 | 4 | 3 | 1 | 0 |
| 设置 | 4 | 3 | 1 | 0 |
| 支付 | 3 | 2 | 1 | 0 |
| 消息 | 4 | 3 | 1 | 0 |
| 生产力 | 3 | 2 | 1 | 0 |
| 健康 | 3 | 2 | 1 | 0 |
| **总计** | **46** | **33** | **10** | **3** |

路径长度: 1-20步 | 平均: 3.8步

---

## 📈 核心指标

### 路径成功率 (Path Success Rate)

```
✓ 查询成功 AND 步数误差 ≤ ±2

目标: ≥70%
计算: 成功路径 / 总路径 × 100%
```

**示例**:
- 46路径中33成功 = 71.7% ✅

### 步骤效率 (Step Efficiency)

```
公式: (随机步数 - KG步数) / 随机步数 × 100%

随机步数 = GT步数 × 3
KG步数 = 知识图谱返回步数

目标: ≥60%
```

**示例**:
- GT: 3步 | 随机: 9步 | KG: 3步 = (9-3)/9 = 66.7% ✅

---

## 📚 重要文档

| 文件 | 用途 | 适合 |
|------|------|------|
| **GETTING_STARTED_EVALUATION.md** | 完整入门指南 | 首次使用者 |
| **EVALUATION_READY.md** | 项目现状概览 | 了解整体 |
| **experiments/EVALUATION_GUIDE.md** | 评估详解 | 深入理解 |
| **CLAUDE.md** | 系统架构 | 开发者 |
| **OPTIMIZATION_SUMMARY.md** | 性能优化 | 优化者 |

**推荐**: 先读 `GETTING_STARTED_EVALUATION.md` ⭐

---

## 🔧 常用命令

### 1. 运行完整评估

```bash
python3 experiments/standalone_evaluation.py \
  --hmtest-dir experiments/hmtest_synthetic_data \
  --output evaluation_results.json \
  --verbose
```

### 2. 查看数据集统计

```bash
cat experiments/hmtest_synthetic_data/DATASET_SUMMARY.md
```

### 3. 检查特定应用

```bash
# 查看电商应用的路径
cat experiments/hmtest_synthetic_data/com.example.shopping/paths.json | python3 -m json.tool
```

### 4. 诊断知识图谱

```bash
python3 << 'EOF'
from agent_interface import KGClient
kg = KGClient()
stats = kg.get_graph_stats()
print(f"节点数: {stats.get('num_nodes')}")
print(f"边数: {stats.get('num_edges')}")
print(f"平均度数: {stats.get('avg_degree')}")
EOF
```

### 5. 测试单个路径查询

```bash
python3 << 'EOF'
from agent_interface import KGClient

kg = KGClient()

# 查询路径
result = kg.query_path(
    app_id="com.example.shopping",
    intent="搜索手机",
    current_page="home",
    max_steps=10
)

print(f"成功: {result.get('success')}")
print(f"步数: {result.get('steps')}")
print(f"置信度: {result.get('confidence')}")
EOF
```

---

## 🐛 快速诊断

### 问题: 路径成功率低

**第1步**: 检查KG构建
```bash
python3 -c "from agent_interface import KGClient; kg = KGClient(); print(kg.get_graph_stats())"
```

**第2步**: 检查页面匹配
```python
# 在kg_query/page_matcher.py中添加日志
print(f"匹配页面: {page_name} -> {matched_page}")
```

**第3步**: 增加max_path_length
```yaml
# config/config.yaml
query:
  max_path_length: 25  # 从10改为25
```

### 问题: 长路径准确率低

**原因**: 可能超过路径长度限制

**解决**:
1. 增大 `max_path_length` (推荐20-30)
2. 改进 `page_matcher.py` 的相似度计算
3. 调整 `path_finder.py` 的权重函数

---

## 📋 工作流程

### 今天 (30分钟)

- [ ] 读 GETTING_STARTED_EVALUATION.md
- [ ] 运行评估脚本
- [ ] 查看 evaluation_results.json
- [ ] 记录首轮结果

### 本周 (2-3天)

- [ ] 分析失败路径
- [ ] 诊断问题原因
- [ ] 修改代码优化
- [ ] 重新运行评估
- [ ] 记录改进效果

### 下周 (2-3天)

- [ ] 迁移到真实HmTest数据
- [ ] 调整Ground Truth JSON格式
- [ ] 运行完整数据集评估
- [ ] 撰写论文实验部分

---

## 🎓 核心概念

### Ground Truth (GT)

```json
{
  "intent": "搜索手机",
  "start_page": "home",
  "end_page": "search_results",
  "operations": [
    {"action": "click", "target_page": "search"},
    {"action": "input", "text": "iPhone 15"},
    {"action": "click", "target_page": "search_results"}
  ]
}
```

**意义**: 标注的正确路径，用于评估

### 知识图谱 (KG)

```
页面 (Nodes):
  home → search → search_results → product_detail

转换 (Edges):
  home --[click搜索]--> search
  search --[input搜索框]--> search
  search --[click确认]--> search_results
```

**意义**: 学习的页面转换模型，用于路径规划

### 路径查询

```
输入: app_id="com.example.shopping", intent="搜索手机"
过程: home -> search -> search_results (3步)
输出: {"success": true, "steps": 3, "confidence": 0.95}
```

---

## ✅ 成功标准

| 指标 | 目标 | 保守 | 理想 |
|------|------|------|------|
| 路径成功率 | ≥70% | 60% | 80% |
| 步骤效率 | ≥60% | 50% | 75% |
| 短路径准确 | - | 75% | 90% |
| 中等路径准确 | - | 60% | 75% |
| 长路径准确 | - | 45% | 70% |

**达成条件**: 至少达到"目标"列的指标

---

## 🚀 一键运行脚本

保存为 `run_evaluation.sh`:

```bash
#!/bin/bash
set -e

cd /Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph

echo "🚀 开始知识图谱评估..."
echo ""

# 1. 检查环境
python3 -c "import networkx, numpy, pydantic; print('✓ 依赖检查通过')"

# 2. 运行评估
python3 experiments/standalone_evaluation.py \
  --hmtest-dir experiments/hmtest_synthetic_data \
  --output evaluation_results.json

# 3. 显示结果
echo ""
echo "📊 评估完成！"
cat evaluation_results.json | python3 -m json.tool

# 4. 汇总
python3 << 'EOF'
import json
with open('evaluation_results.json') as f:
    r = json.load(f)
print("\n" + "="*50)
print("✅ 最终结果:")
print(f"  路径成功率: {r['path_success_rate']:.1f}%")
print(f"  步骤效率:   {r['step_efficiency']:.1f}%")
print("="*50)
EOF
```

运行:
```bash
chmod +x run_evaluation.sh
./run_evaluation.sh
```

---

## 📞 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| ModuleNotFoundError | 依赖缺失 | `pip install -r requirements.txt` |
| FileNotFoundError | 文件不在 | `ls experiments/hmtest_synthetic_data/` |
| ValueError | 数据格式错 | 检查paths.json格式 |
| LowAccuracy | KG不完整 | 检查add_page/report_transition调用 |

---

## 📊 结果解读

### 优秀结果 (Green)
```
路径成功率: 75-85% ✅
步骤效率:   65-75% ✅
长路径准确: 65%+ ✅
```

### 合格结果 (Yellow)
```
路径成功率: 65-75% ⚠️
步骤效率:   55-65% ⚠️
需要小幅优化
```

### 需要改进 (Red)
```
路径成功率: <65% ❌
步骤效率:   <55% ❌
需要大幅优化
```

---

## 🔄 优化循环

```
1. 运行评估
   ↓
2. 检查结果
   ↓
3. 分析失败路径
   ↓
4. 诊断原因
   ↓
5. 修改代码
   ↓
6. 重新运行
   ↓
[重复直到达到目标]
```

---

## 📝 记录模板

```
评估日期: 2026-02-15
数据集: hmtest_synthetic_data
运行时间: 8.5秒

结果:
  路径成功率: 71.7%
  步骤效率:   63.2%
  短路径准确率: 85%
  中等路径准确率: 72%
  长路径准确率: 58%

观察:
  ✓ 路径成功率已达到目标
  ⚠️ 长路径还有改进空间

修改项:
  1. 增大max_path_length → 25
  2. 改进page_matcher相似度算法

下次运行目标: 75%+ 路径成功率
```

---

## 🎯 关键文件位置

```
根目录/
├── GETTING_STARTED_EVALUATION.md    ⭐ 从这里开始
├── EVALUATION_READY.md              🎯 项目状态
├── QUICK_REFERENCE.md               📖 本文档
├── CLAUDE.md                        🏗️ 架构文档
├── OPTIMIZATION_SUMMARY.md          ⚡ 优化说明
│
└── experiments/
    ├── standalone_evaluation.py     🔧 核心脚本
    ├── hmtest_synthetic_dataset.py  📊 数据生成
    ├── EVALUATION_GUIDE.md          📚 详细指南
    ├── sample_ground_truth.json     📄 格式示例
    ├── quick_start.sh               🚀 快速脚本
    └── hmtest_synthetic_data/       📦 生成的46条路径
```

---

## 💡 Pro Tips

1. **调试时添加日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **批量测试**
   ```bash
   for i in {1..5}; do python3 ...; done
   ```

3. **性能分析**
   ```python
   import time
   start = time.time()
   # ... 代码 ...
   print(f"耗时: {time.time()-start:.3f}s")
   ```

4. **对比结果**
   ```bash
   diff evaluation_results_v1.json evaluation_results_v2.json
   ```

---

**🚀 现在就开始吧！**

👉 运行这个命令:
```bash
python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data
```

👉 然后阅读:
- GETTING_STARTED_EVALUATION.md
- evaluation_results.json
