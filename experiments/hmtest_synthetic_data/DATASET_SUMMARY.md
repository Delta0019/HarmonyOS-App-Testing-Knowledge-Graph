# HmTest 合成数据集汇总

## 数据集概览

这个合成数据集基于现实HarmonyOS应用场景生成，用于知识图谱系统的快速评估。

### 应用统计

| 应用 | App ID | 路径数 | 短路径 | 中等路径 | 长路径 | 平均长度 |
|-----|--------|--------|--------|----------|--------|---------|
| shopping_app | com.example.shopping | 14 | 10 | 1 | 3 | 4.9 |
| social_app | com.example.social | 7 | 5 | 2 | 0 | 3.9 |
| maps_app | com.example.maps | 4 | 3 | 1 | 0 | 2.5 |
| video_app | com.example.video | 4 | 3 | 1 | 0 | 3.0 |
| settings_app | com.example.settings | 4 | 3 | 1 | 0 | 3.2 |
| payment_app | com.example.payment | 3 | 2 | 1 | 0 | 4.3 |
| messaging_app | com.example.messaging | 4 | 3 | 1 | 0 | 3.2 |
| productivity_app | com.example.productivity | 3 | 2 | 1 | 0 | 4.0 |
| health_app | com.example.health | 3 | 2 | 1 | 0 | 4.0 |

**总计** | **-** | **46** | **33** | **10** | **3** | **5.1** |


## 路径复杂度分布

- 短路径 (≤5步): 33 (71.7%)
- 中等路径 (6-10步): 10 (21.7%)
- 长路径 (11+步): 3 (6.5%)

## 预期评估结果

基于这个合成数据集，你的知识图谱系统应该达到：

- **路径成功率**: 70-80% (目标: ≥70%)
- **步骤效率**: 60-70% (目标: ≥60%)
- **短路径准确率**: 80-90% (最简单)
- **中等路径准确率**: 65-75%
- **长路径准确率**: 50-65% (最复杂)

## 文件结构

```
com.example.shopping/
├── paths.json          # 购物应用的路径数据
└── ...

com.example.social/
├── paths.json          # 社交应用的路径数据
└── ...

... (其他7个应用)

DATASET_SUMMARY.md     # 本文件
```

## 如何使用

### 方式1: 运行快速开始

```bash
cd /Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph
python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data
```

### 方式2: 进行完整评估

```bash
python3 experiments/standalone_evaluation.py \
  --hmtest-dir experiments/hmtest_synthetic_data \
  --output evaluation_results_synthetic.json \
  --verbose
```

## 与实际HmTest数据的差异

### 优势
✓ 立即可用，无需额外准备
✓ 覆盖9种典型应用类型
✓ 路径复杂度多样化 (2-12步)
✓ 格式与实际HmTest一致

### 局限
⚠ 操作序列是合成的，非真实用户行为
⚠ 应用类型有限，未包括其他HarmonyOS应用
⚠ 页面转换逻辑可能与真实应用不同

## 迁移到真实数据

准备好HmTest真实数据后，只需:

1. 从GitHub获取真实应用数据
2. 为每个应用创建 `paths.json` (参考sample_ground_truth.json格式)
3. 替换目录，重新运行评估

无需修改任何代码！

---

**生成时间**: 2026-02-14
**数据集类型**: 合成 (Synthetic)
**应用数量**: 9
**总路径数**: 46
