# 🚀 知识图谱系统评估入门指南

**最后更新**: 2026-02-15

## 概述

这份指南帮助你快速验证知识图谱系统的性能，**无需外部Agent**，使用合成HmTest数据集。

### 核心目标

评估系统是否达到：
- ✅ **路径成功率**: ≥70% (查询成功且步数准确)
- ✅ **步骤效率**: ≥60% (相比随机探索的效率提升)
- ✅ **多样性稳定性**: 短/中/长路径都能有效处理

---

## 📊 数据集说明

### 数据位置
```
experiments/hmtest_synthetic_data/
├── com.example.shopping/        # 电商应用 (12条路径)
├── com.example.social/          # 社交应用 (8条路径)
├── com.example.maps/            # 地图应用 (4条路径)
├── com.example.video/           # 视频应用 (4条路径)
├── com.example.settings/        # 设置应用 (4条路径)
├── com.example.payment/         # 支付应用 (3条路径)
├── com.example.messaging/       # 消息应用 (4条路径)
├── com.example.productivity/    # 生产力应用 (3条路径)
├── com.example.health/          # 健康应用 (3条路径)
└── DATASET_SUMMARY.md           # 数据集统计报告
```

### 数据统计

```
总应用数: 9
总路径数: 46

路径复杂度分布:
├─ 短路径 (≤5步):    33条 (71.7%) - 快速操作，如搜索、打开页面
├─ 中等路径 (6-10步): 10条 (21.7%) - 中等复杂度，如购物、发帖
└─ 长路径 (11+步):    3条 (6.5%)  - 复杂流程，如完整购物、设置管理
```

### 每个应用的文件格式

每个应用目录包含 `paths.json`:

```json
{
  "app_name": "shopping_app",
  "app_id": "com.example.shopping",
  "paths": [
    {
      "intent": "搜索手机",
      "start_page": "home",
      "end_page": "search_results",
      "operations": [
        {
          "action_type": "click",
          "widget_id": "btn_search",
          "widget_text": "搜索",
          "target_page": "search"
        },
        {
          "action_type": "input",
          "widget_id": "input_search",
          "widget_text": "搜索框",
          "input_text": "iPhone 15",
          "target_page": "search"
        },
        {
          "action_type": "click",
          "widget_id": "btn_submit",
          "widget_text": "搜索",
          "target_page": "search_results"
        }
      ]
    }
  ],
  "statistics": {
    "total_paths": 12,
    "short_paths": 10,
    "medium_paths": 1,
    "long_paths": 1,
    "total_operations": 35,
    "average_path_length": 2.9
  }
}
```

---

## 🏃 快速开始（5分钟）

### 方案A: 运行完整评估

```bash
cd /Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph

# 运行评估框架（使用合成数据）
python3 experiments/standalone_evaluation.py \
  --hmtest-dir experiments/hmtest_synthetic_data \
  --output evaluation_results.json

# 查看结果
cat evaluation_results.json | python3 -m json.tool
```

### 方案B: 逐步运行（推荐用于调试）

```bash
# 1. 检查数据集
python3 << 'EOF'
import json
import os

data_dir = "experiments/hmtest_synthetic_data"
for app_id in os.listdir(data_dir):
    app_path = os.path.join(data_dir, app_id, "paths.json")
    if os.path.exists(app_path):
        with open(app_path) as f:
            data = json.load(f)
            stats = data.get("statistics", {})
            print(f"{app_id}: {stats.get('total_paths')} 条路径 "
                  f"(短:{stats.get('short_paths')} 中:{stats.get('medium_paths')} 长:{stats.get('long_paths')})")
EOF

# 2. 构建知识图谱
python3 << 'EOF'
from experiments.standalone_evaluation import GroundTruthLoader, StandaloneEvaluator

loader = GroundTruthLoader()
paths = loader.load_from_directory("experiments/hmtest_synthetic_data")
print(f"✓ 加载了 {len(paths)} 个应用的数据")

evaluator = StandaloneEvaluator()
evaluator.build_knowledge_graph(paths)
print("✓ 知识图谱已构建")

# 3. 查询路径
results = evaluator.query_paths(paths)
print(f"✓ 查询了 {len(results)} 条路径")

# 4. 计算指标
metrics = evaluator.evaluate(results)
print("\n📊 评估结果:")
print(f"  路径成功率: {metrics.path_success_rate:.1f}%")
print(f"  步骤效率:   {metrics.step_efficiency:.1f}%")
EOF
```

---

## 📈 理解结果

### 核心指标说明

#### 1. **路径成功率** (Path Success Rate)

```
成功条件：
1. KG查询成功（找到路径）
2. 返回的步数与GT步数相差≤2（允许±2的误差）

计算：成功路径数 / 总路径数 × 100%

目标: ≥70%
```

示例：
- 46条路径中，32条成功 → 69.6% (略低于目标)
- 46条路径中，33条成功 → 71.7% (达到目标)

#### 2. **步骤效率** (Step Efficiency)

```
公式：(随机步数 - KG步数) / 随机步数 × 100%

其中：
- 随机步数 = GT步数 × 3 (模拟随机Agent需3倍步数)
- KG步数 = 知识图谱返回的步数

目标: ≥60%
```

示例：
```
GT路径: home → search → search_results (3步)
随机Agent: 需要 3×3 = 9步
KG系统: 返回 3步
效率: (9-3)/9 × 100% = 66.7% ✓
```

#### 3. **多样性分析**

按路径复杂度分别统计准确率：

```
短路径 (≤5步):    应该 ≥85% 准确率 (最简单，易成功)
中等路径 (6-10步): 应该 ≥70% 准确率 (中等难度)
长路径 (11+步):   应该 ≥60% 准确率 (最复杂，最难)
```

---

## 🔍 诊断低分原因

如果结果低于预期，按顺序检查：

### 问题1: 路径成功率低 (<60%)

**可能原因**：
1. 知识图谱构建不完整
2. 页面名称不匹配
3. 路径查询算法问题

**诊断方法**：
```python
# 检查KG中的页面数量
from agent_interface import KGClient
kg = KGClient()
stats = kg.get_graph_stats()
print(f"图中页面数: {stats.get('num_nodes')}")
print(f"图中转换数: {stats.get('num_edges')}")
print(f"平均度数: {stats.get('avg_degree')}")

# 检查特定应用的KG
kg_export = kg.export_graph()
print(f"应用: {list(kg_export.keys())}")
```

**解决方案**：
- 检查 `kg_builder/graph_builder.py` 中的构建逻辑
- 打印调试日志，确认每个应用的页面都被添加了
- 验证page_id格式是否一致

### 问题2: 长路径准确率特别低 (<40%)

**可能原因**：
1. 路径查询超出 `max_path_length` 限制
2. 复杂路径中的页面匹配错误
3. 路径搜索算法选择了次优路径

**诊断方法**：
```python
# 运行单个长路径查询
evaluator = StandaloneEvaluator()
long_path = paths["shopping"][0]  # 第一个长路径

result = evaluator.query_single_path(long_path)
print(f"预期步数: {len(long_path['operations'])}")
print(f"KG步数:  {result['kg_steps']}")
print(f"置信度:  {result['confidence']}")
print(f"返回的路径: {result['path']}")
```

**解决方案**：
- 增大 `config.yaml` 中的 `max_path_length`（推荐: 20-30）
- 改进 `kg_query/page_matcher.py` 的相似度计算
- 检查是否有多条等效路径，选择最短的

---

## 💡 优化建议

### 优化1: 改进页面匹配

**当前**: 精确名称匹配
**推荐**: 增加模糊匹配

```python
# 在 page_matcher.py 中
def match_page(self, page_name: str, threshold=0.8):
    # 不仅检查精确匹配
    for pg in self.pages:
        if pg.name == page_name:
            return pg

        # 还检查相似度
        similarity = fuzzy_match(page_name, pg.name)
        if similarity > threshold:
            return pg
```

### 优化2: 改进路径查找权重

**当前**: 简单的BFS或Dijkstra
**推荐**: 结合成功率和步数的多因素权重

```python
# 权重公式示例
weight = (1 - success_rate) + 0.5 * steps
```

### 优化3: 缓存常用路径

对频繁查询的路径进行缓存，加速评估：

```python
class PathCache:
    def __init__(self):
        self.cache = {}

    def get(self, app_id, intent, start_page):
        key = f"{app_id}#{intent}#{start_page}"
        return self.cache.get(key)

    def set(self, app_id, intent, start_page, path):
        key = f"{app_id}#{intent}#{start_page}"
        self.cache[key] = path
```

---

## 🎯 预期结果范围

基于系统设计，预期达到：

| 指标 | 保守估计 | 目标 | 理想情况 |
|------|---------|------|---------|
| **路径成功率** | 60% | ≥70% | 80% |
| **步骤效率** | 50% | ≥60% | 75% |
| **短路径准确率** | 75% | 85% | 95% |
| **中等路径准确率** | 60% | 70% | 80% |
| **长路径准确率** | 45% | 60% | 75% |

---

## 📝 运行完整的实验

### 第1步: 准备环境

```bash
cd /Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph

# 检查依赖
python3 -c "import networkx, numpy, pydantic; print('✓ 依赖完整')"
```

### 第2步: 运行基准测试

```bash
# 使用合成数据运行
python3 experiments/standalone_evaluation.py \
  --hmtest-dir experiments/hmtest_synthetic_data \
  --output evaluation_results_synthetic.json \
  --verbose

# 查看详细结果
cat evaluation_results_synthetic.json | python3 -m json.tool
```

### 第3步: 分析结果

```bash
# 生成HTML报告（可选）
python3 << 'EOF'
import json

with open('evaluation_results_synthetic.json') as f:
    results = json.load(f)

print("=" * 50)
print("📊 知识图谱系统评估结果")
print("=" * 50)
print(f"\n总路径数: {results['total_paths']}")
print(f"成功路径: {results['successful_paths']}")
print(f"路径成功率: {results['path_success_rate']:.1f}%")
print(f"步骤效率: {results['step_efficiency']:.1f}%")

if "diversity_analysis" in results:
    print("\n多样性分析:")
    for level, acc in results['diversity_analysis'].items():
        print(f"  {level}: {acc:.1f}%")

print(f"\n评估完成时间: {results.get('evaluation_time', 'N/A')}")
print("=" * 50)
EOF
```

### 第4步: 迭代优化

如果结果低于目标：

1. **诊断问题**
   ```bash
   python3 -c "from kg_core.graph_store import MemoryGraphStore; ..."
   ```

2. **修改代码**
   - 编辑相关模块（见下文）
   - 添加日志调试

3. **重新运行**
   ```bash
   python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data
   ```

---

## 🛠️ 关键文件说明

### 评估框架

- **`experiments/standalone_evaluation.py`** (600+ 行)
  - `GroundTruthLoader`: 从JSON加载标注数据
  - `StandaloneEvaluator`: 执行完整评估流程
  - `EvaluationMetrics`: 计算和存储指标

- **`experiments/EVALUATION_GUIDE.md`**
  - Ground Truth格式详解
  - 评估指标定义
  - 常见问题解答

- **`experiments/sample_ground_truth.json`**
  - 5条示例路径
  - 演示正确的JSON格式

### 知识图谱系统

- **`agent_interface/kg_client.py`**
  - `KGClient`: Agent的主接口
  - `query_path()`: 查询完整路径
  - `get_next_action()`: 获取下一步操作

- **`kg_core/graph_store.py`**
  - `MemoryGraphStore`: 内存图数据库实现
  - `get_outgoing_transitions()`: 查询出度转换

- **`kg_query/path_finder.py`**
  - `PathFinder`: 路径规划算法
  - `find_path_by_intent()`: 意图驱动的路径搜索

- **`kg_query/page_matcher.py`**
  - `PageMatcher`: 页面匹配算法
  - `match_page()`: UI到已知页面的映射

---

## 🔄 使用真实HmTest数据

当你准备好HmTest真实数据时：

### 步骤1: 获取真实数据

```bash
# 方案A: 从GitHub获取（如果有数据发布）
git clone https://github.com/sqlab-sustech/hmtest.git

# 方案B: 从论文补充材料获取
# 查看论文: https://jcst.ict.ac.cn/article/doi/10.1007/s11390-025-5142-4
```

### 步骤2: 准备Ground Truth JSON

如果HmTest数据是PTG (Page Transition Graph) 格式，需要转换：

```python
# scripts/convert_ptg_to_ground_truth.py
import json

def convert_ptg_to_ground_truth(ptg_file):
    """将PTG转换为Ground Truth格式"""
    with open(ptg_file) as f:
        ptg = json.load(f)

    # 从PTG中提取路径
    # ... 转换逻辑 ...

    return {
        "app_name": ...,
        "app_id": ...,
        "paths": [...]
    }
```

### 步骤3: 运行评估

```bash
python3 experiments/standalone_evaluation.py --hmtest-dir /path/to/real/data
```

---

## ❓ 常见问题

**Q1: 评估需要多久？**
A: 46条路径的完整评估通常需要 5-10 秒。

**Q2: 可以修改max_path_length吗？**
A: 可以。在 `config/config.yaml` 中修改 `query.max_path_length`。建议值: 15-30。

**Q3: 如何添加新的应用？**
A: 在 `experiments/hmtest_synthetic_data/` 中新建目录，按照格式创建 `paths.json`。

**Q4: 如果页面匹配失败怎么办？**
A: 检查 `kg_query/page_matcher.py` 中的相似度阈值，或改进匹配算法。

**Q5: 评估结果能导出为其他格式吗？**
A: 可以。修改 `standalone_evaluation.py` 中的结果导出部分即可。

---

## 📚 进一步阅读

- **[CLAUDE.md](CLAUDE.md)** - 项目开发指南
- **[EVALUATION_GUIDE.md](experiments/EVALUATION_GUIDE.md)** - 评估框架详解
- **[OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)** - 代码优化说明
- **[API_SPECIFICATION.md](API_SPECIFICATION.md)** - API参考

---

## ✅ 检查清单

在运行评估前，确保完成以下步骤：

- [ ] 已安装所有依赖 (`pip install -r requirements.txt`)
- [ ] 已生成合成数据集 (`experiments/hmtest_synthetic_data/`)
- [ ] 已检查数据格式正确 (运行第一个诊断脚本)
- [ ] 已理解核心指标 (路径成功率、步骤效率)
- [ ] 已备份原始代码 (如果要进行修改)

---

## 🚀 下一步

1. **现在**: 运行快速开始，获得第一个结果
   ```bash
   python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data
   ```

2. **今天**: 分析结果，诊断任何问题

3. **本周**: 优化系统以提高指标

4. **下周**: 迁移到真实HmTest数据

5. **最后**: 撰写论文实验章节

---

**需要帮助？** 查看相关的CLAUDE.md或EVALUATION_GUIDE.md。
