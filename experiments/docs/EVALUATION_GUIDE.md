# 知识图谱独立评估框架

## 概述

这是一个**不依赖外部Agent**的完整评估框架，直接用HmTest数据集测试你的知识图谱系统。

**核心思路**：
```
HmTest数据集 → 提取Ground Truth路径 → 构建KG → 查询路径 → 对比分析 → 计算指标
```

---

## 快速开始

### 第1步：准备HmTest数据集

```bash
# 克隆HmTest仓库
git clone https://github.com/sqlab-sustech/hmtest.git
cd hmtest

# 查看数据集结构
ls -la data/apps/

# 预期结构：
# data/apps/
# ├── app1/
# │   ├── paths.json (或 ground_truth.json)
# │   └── ...
# ├── app2/
# └── ...
```

### 第2步：准备Ground Truth路径数据

为每个HmTest应用创建 `paths.json` 文件（格式见下面示例）：

```bash
# 在每个应用目录下
cd hmtest/data/apps/app1
cat > paths.json << 'EOF'
{
  "paths": [
    {
      "intent": "搜索商品",
      "start_page": "home",
      "end_page": "search_results",
      "operations": [
        {
          "action_type": "click",
          "widget_id": "search_btn",
          "widget_text": "搜索",
          "target_page": "search"
        },
        {
          "action_type": "input",
          "widget_id": "search_input",
          "widget_text": "",
          "input": "手机",
          "target_page": "search"
        },
        {
          "action_type": "click",
          "widget_id": "search_btn",
          "widget_text": "搜索",
          "target_page": "search_results"
        }
      ]
    }
  ]
}
EOF
```

### 第3步：运行评估

```bash
cd /path/to/HarmonyOS-App-Testing-Knowledge-Graph

# 运行评估框架
python experiments/standalone_evaluation.py --hmtest-dir /path/to/hmtest/data/apps

# 查看结果
cat evaluation_results.json
tail -f evaluation.log
```

---

## Ground Truth JSON 格式详解

### 完整示例

```json
{
  "paths": [
    {
      "intent": "搜索商品",
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
          "widget_id": "input_keyword",
          "widget_text": "输入关键词",
          "input": "iPhone 15",
          "target_page": "search"
        },
        {
          "action_type": "click",
          "widget_id": "btn_search_confirm",
          "widget_text": "确定",
          "target_page": "search_results"
        }
      ]
    },
    {
      "intent": "查看商品详情",
      "start_page": "search_results",
      "end_page": "product_detail",
      "operations": [
        {
          "action_type": "click",
          "widget_id": "item_0",
          "widget_text": "iPhone 15 Pro",
          "target_page": "product_detail"
        }
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `intent` | ✅ | 用户意图，如"搜索商品" |
| `start_page` | ✅ | 起始页面名称 |
| `end_page` | ✅ | 目标页面名称 |
| `operations` | ✅ | 操作序列数组 |
| `action_type` | ✅ | 操作类型：click, input, swipe, back等 |
| `widget_id` | ✅ | 控件唯一ID |
| `widget_text` | ✅ | 控件显示文本 |
| `input` | ❌ | input操作的输入文本 |
| `target_page` | ✅ | 该操作导致的目标页面 |

---

## 评估指标说明

### 核心指标

#### 1. **路径成功率** (Path Success Rate)
```
成功率 = 知识图谱查询成功且步数正确 / 总路径数 × 100%

评判标准：
- KG查询成功
- 返回的路径步数与GT步数相差≤2
- 目标: ≥70%
```

#### 2. **步骤效率** (Step Efficiency)
```
效率 = (随机步数 - KG步数) / 随机步数 × 100%

其中：
- 随机步数 = GT步数 × 3 (模拟随机Agent需要3倍步数)
- KG步数 = 知识图谱返回的步数
- 目标: ≥60%
```

### 辅助指标

#### 多样性分析
```
按照GT路径长度分类分析准确率：

短路径 (≤5步):    评估快速任务准确率
中等路径 (6-10步): 评估中等复杂度任务准确率
长路径 (11+步):   评估复杂任务准确率

目的：观察你的系统在不同难度下的表现
```

---

## 评估流程详解

### 第0步：加载数据
```python
loader = GroundTruthLoader()
ground_truth_paths = loader.load_from_directory("hmtest/data/apps")
# 加载所有应用的ground truth路径
```

### 第1步：构建知识图谱
```python
evaluator.build_knowledge_graph(ground_truth_paths)

执行内容：
1. 提取所有GT路径中的页面
2. 添加页面到KG（add_page）
3. 添加页面转换（report_transition）
4. 注册意图（register_intent）
```

### 第2步：查询路径
```python
query_results = evaluator.query_paths(ground_truth_paths)

对每条GT路径：
1. 调用 kg.query_path(app_id, intent, start_page)
2. 记录KG返回的步数和置信度
3. 对比GT步数
```

### 第3步：对比和计算
```python
metrics = evaluator.evaluate(query_results)

计算：
1. 路径成功率 = 成功/总数
2. 步骤效率 = (随机步数-KG步数)/随机步数
3. 多样性分析 = 按路径长度分组统计
```

---

## 实验数据预期

### 典型结果范围

| 指标 | 差 | 良好 | 优秀 |
|------|-----|------|------|
| 路径成功率 | <50% | 50-70% | >70% |
| 步骤效率 | <30% | 30-60% | >60% |
| 短路径准确率 | <60% | 60-80% | >80% |
| 长路径准确率 | <40% | 40-70% | >70% |

### 真实数据集的特性

从HmTest论文和我们的分析，预期数据集应该有：

```
应用数量: 9个 (电商、社交、工具等混合)
平均页面数: 10-20页/应用
路径数: 20-30条/应用
操作多样性:
  - 短路径 (≤5步): 40%
  - 中等路径 (6-10步): 35%
  - 长路径 (11+步): 25%
```

---

## 常见问题

### Q1: 没有找到paths.json，怎么办？

**A**: HmTest可能使用不同的格式。尝试以下：

```bash
# 查找可能的格式
find hmtest/data/apps -name "*.json" | head -20

# 如果是其他格式，需要编写converter
# 例如：如果是PTG格式，需要手工标注操作序列
```

### Q2: 如果HmTest数据量太少（9个应用），怎么办？

**A**: 有以下两个方案：

**方案A：补充开源应用（推荐）**
```bash
# 找10个开源HarmonyOS应用
# GitHub搜索: "harmonyos" language:Java stars:>100

# 手动标注其路径 (比较耗时)
```

**方案B：数据增强**
```python
# 在现有9个应用基础上，为每个应用多标注5-10条路径
# 总共可以达到 9 × (20 + 10) = 270条路径
```

### Q3: 路径成功率很低，原因可能是什么？

**A**: 诊断方法：

1. **检查KG构建**
   ```bash
   # 查看是否所有页面和转换都添加了
   python -c "from agent_interface import KGClient; kg = KGClient(); print(kg.get_graph_stats())"
   ```

2. **检查页面匹配**
   - 页面名称是否精确匹配
   - 是否需要模糊匹配

3. **检查路径规划**
   - 使用 `kg.query_path(..., max_steps=30)` 增大搜索空间
   - 检查置信度是否太低

---

## 预期的论文结果

基于你的系统和HmTest数据集，预期结果应该是：

```
【路径成功率】
- Random Agent: 30-40%
- Rule-based: 50-60%
- Your KG System: 65-75% ← 目标

【步骤效率】
- Random Agent: 0% (基线)
- Rule-based: 20-40%
- Your KG System: 50-70% ← 目标

【多样性分析】
- 短路径 (≤5步): 75-85% 准确率
- 中等路径 (6-10步): 65-75% 准确率
- 长路径 (11+步): 55-65% 准确率
```

如果你能达到这些数字，说明系统已经相当可靠！

---

## 下一步

1. **准备数据** (1周)
   - 下载HmTest
   - 为每个应用标注ground truth路径 (或等待论文数据发布)

2. **运行评估** (1-2天)
   - 执行evaluation框架
   - 观察结果

3. **分析结果** (1周)
   - 诊断问题
   - 优化算法 (如果需要)

4. **论文写作** (2周)
   - 记录实验设置
   - 分析为什么/为什么不
   - 与相关工作对比

---

## 脚本改进建议

当前脚本可以进一步改进：

```python
# 1. 支持多个Ground Truth格式 (PTG、STG等)
# 2. 添加可视化 (绘制成功率曲线)
# 3. 添加统计测试 (显著性检验)
# 4. 支持增量评估 (只评估新应用)
# 5. 生成HTML报告
```

---

**更新日期**: 2026-02-14
**脚本位置**: `experiments/standalone_evaluation.py`
