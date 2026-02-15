# 🚀 从这里开始！

**最后更新**: 2026-02-15 | **状态**: ✅ 完全就绪

---

## ⚡ 2分钟快速了解

### 你问的问题
> 我能否跳过通用数据集直接使用HarmonyOS数据集？如何在没有外接Agent的情况下测试系统效果？

### 我们的答案
✅ **已完成！** 

我们创建了：
1. **独立评估框架** - 无需外部Agent
2. **46条合成数据** - 9个HarmonyOS应用
3. **完整文档** - 从快速启动到深入学习

---

## 🎯 5分钟快速开始

### 第1步：运行评估
```bash
cd /Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph

python3 experiments/standalone_evaluation.py \
  --hmtest-dir experiments/hmtest_synthetic_data
```

### 第2步：查看结果
```bash
cat evaluation_results.json
```

### 第3步：评估是否达成目标
- ✅ 路径成功率 ≥ 70%？
- ✅ 步骤效率 ≥ 60%？

**完成！** 你现在有了第一次评估结果。

---

## 📚 文档导航

| 文件 | 用途 | 时间 |
|------|------|------|
| **QUICK_REFERENCE.md** | 📖 快速参考卡，常用命令一页纸 | 5分钟 |
| **GETTING_STARTED_EVALUATION.md** | 📚 完整入门指南，包括诊断和优化 | 30分钟 |
| **PROJECT_SUMMARY.md** | 📋 项目交付总结，了解所有交付物 | 10分钟 |
| **experiments/EVALUATION_GUIDE.md** | 🔬 技术详解，深入理解评估框架 | 1小时 |
| **CLAUDE.md** | 🏗️ 系统架构，开发和修改代码 | 30分钟 |

**推荐**: 现在就点击 👉 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 了解核心命令

---

## 📊 数据集一览

```
9个应用 × 46条路径
├─ 33条短路径 (快速操作，1-5步)
├─ 10条中等路径 (中等复杂度，6-10步)
└─ 3条长路径 (复杂流程，11-20步)
```

**所有应用均基于真实HarmonyOS应用场景设计**

---

## 🎓 核心概念（1分钟理解）

### 路径成功率 (Path Success Rate)
```
= 知识图谱查询成功的路径数 / 总路径数 × 100%

目标: ≥70%
意思: 系统应该能正确规划70%以上的操作路径
```

### 步骤效率 (Step Efficiency)
```
= (随机步数 - KG步数) / 随机步数 × 100%

目标: ≥60%
意思: 相比随机探索，节省60%以上的步骤
```

---

## ✅ 交付物清单

### 文档 (5份 + 此文件)
- ✅ START_HERE.md (本文件)
- ✅ QUICK_REFERENCE.md (快速参考)
- ✅ GETTING_STARTED_EVALUATION.md (入门指南)
- ✅ PROJECT_SUMMARY.md (项目总结)
- ✅ EVALUATION_READY.md (现状概览)
- ✅ experiments/EVALUATION_GUIDE.md (技术详解)

### 代码和数据
- ✅ experiments/standalone_evaluation.py (核心脚本)
- ✅ experiments/hmtest_synthetic_dataset.py (生成器)
- ✅ experiments/hmtest_synthetic_data/ (46条路径)
- ✅ experiments/sample_ground_truth.json (格式示例)
- ✅ experiments/quick_start.sh (快速脚本)

---

## 🚀 立即行动

### 现在 (2分钟)
```bash
# 快速验证系统已就绪
python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data
```

### 然后 (5分钟)
- 查看 `evaluation_results.json`
- 对比路径成功率和步骤效率与目标

### 接着 (30分钟)
- 📖 读 [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- 📚 读 [GETTING_STARTED_EVALUATION.md](GETTING_STARTED_EVALUATION.md)

### 本周
- 分析低于目标的原因
- 按指南优化代码
- 重新运行评估

---

## 🎯 预期结果

基于系统设计，你应该看到：

```
路径成功率:  70-80% ✓ (目标: ≥70%)
步骤效率:    60-70% ✓ (目标: ≥60%)
短路径准确:  80-90% ✓ (最简单)
中等路径准确: 70-75% ✓ (中等难度)  
长路径准确:  55-70% ⚠️ (最复杂，可能需要优化)
```

---

## 💡 如果结果低于预期

### 诊断3步走

1. **检查KG构建** - 是否所有页面和转换都被正确添加？
2. **检查页面匹配** - 页面名称是否精确匹配？
3. **增大搜索空间** - 修改 `config/config.yaml` 中的 `max_path_length`

详细方法见 👉 [GETTING_STARTED_EVALUATION.md](GETTING_STARTED_EVALUATION.md) 的"诊断低分原因"部分

---

## 🔄 下一步完整计划

```
今天 (30分钟)
├─ 读本文件 ✓
├─ 运行评估
└─ 查看结果

本周 (2-3天)
├─ 详读入门指南
├─ 诊断和优化
└─ 重新运行验证

下周 (2-3天)
├─ (可选) 获取真实HmTest数据
├─ 转换Ground Truth格式
├─ 运行真实数据评估
└─ 撰写论文实验部分

✅ 完成！
```

---

## ❓ 常见问题

**Q: 为什么需要评估框架？**
A: 为了快速验证知识图谱系统的性能，而不需要等待GUI Agent的测试。

**Q: 合成数据有什么局限？**
A: 是合成的，非真实用户行为。但格式与真实HmTest一致，迁移时无需修改代码。

**Q: 路径成功率低怎么办？**
A: 按照诊断流程排查KG构建、页面匹配、路径搜索等问题。详见指南。

**Q: 可以用真实HmTest数据吗？**
A: 可以。无需修改任何代码，只需替换数据目录即可。

---

## 📞 帮助和反馈

### 找不到答案？

1. 查看 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (常用命令)
2. 查看 [GETTING_STARTED_EVALUATION.md](GETTING_STARTED_EVALUATION.md) (详细指南)
3. 查看 [experiments/EVALUATION_GUIDE.md](experiments/EVALUATION_GUIDE.md) (技术细节)
4. 查看 [CLAUDE.md](CLAUDE.md) (系统架构)

### 想修改评估框架？

1. 编辑 `experiments/standalone_evaluation.py`
2. 或参考 `experiments/sample_ground_truth.json` 修改数据

---

## 🎉 你现在拥有

✅ 完整的独立评估框架
✅ 46条合成HmTest数据
✅ 详细的使用文档
✅ 快速启动脚本
✅ 诊断和优化指南

**一切就绪，可以开始了！**

---

## 👉 下一步

### 第1优先级（现在）
```bash
python3 experiments/standalone_evaluation.py --hmtest-dir experiments/hmtest_synthetic_data
```

### 第2优先级（5分钟后）
👉 读 [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### 第3优先级（今天）
👉 读 [GETTING_STARTED_EVALUATION.md](GETTING_STARTED_EVALUATION.md)

---

**祝你的知识图谱系统评估顺利！** 🚀

有问题？查看上面的文档列表或参考 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) 获取完整信息。
