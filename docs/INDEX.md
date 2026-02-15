# 📚 文档导航

**项目**: HarmonyOS App自动化测试知识图谱
**状态**: ✅ 完全就绪
**最后更新**: 2026-02-15

---

## 🚀 快速开始

根据你的需求选择相应的文档：

### 场景1: 我想立即运行评估 (5分钟)
👉 [00_START_HERE.md](00_START_HERE.md)
- 3行命令快速启动
- 核心概念一分钟速成
- 预期结果范围

### 场景2: 我想深入学习如何使用 (30分钟)
👉 [02_USER_GUIDE.md](02_USER_GUIDE.md)
- 完整的使用指南
- 指标详解
- 诊断低分原因
- 优化建议

### 场景3: 我想理解系统架构 (1小时)
👉 [03_ARCHITECTURE.md](03_ARCHITECTURE.md)
- 系统整体设计
- 核心模块说明
- 开发指南
- 集成示例

### 场景4: 我想优化代码性能 (30分钟)
👉 [04_OPTIMIZATION.md](04_OPTIMIZATION.md)
- 已完成的优化详解
- 性能基准对比
- 迁移和兼容性
- 未来优化方向

### 场景5: 我想了解API接口 (参考)
👉 [05_API_REFERENCE.md](05_API_REFERENCE.md)
- KGClient完整接口
- 请求和响应格式
- 错误处理
- 集成示例

### 场景6: 我想了解评估框架 (技术细节)
👉 [../experiments/EVALUATION_GUIDE.md](../experiments/EVALUATION_GUIDE.md)
- Ground Truth格式
- 评估流程
- 指标计算公式
- 常见问题

---

## 📋 完整文档列表

### 根目录

| 文件 | 用途 | 重要性 |
|------|------|--------|
| [README.md](../README.md) | 项目概览，性能基准 | ⭐⭐⭐⭐⭐ |
| [INDEX.md](INDEX.md) | 本文档，导航指南 | ⭐⭐⭐⭐ |

### docs/ 目录

| 文件 | 用途 | 阅读时间 | 重要性 |
|------|------|---------|--------|
| [00_START_HERE.md](00_START_HERE.md) | 快速开始，3步启动 | 2分钟 | ⭐⭐⭐⭐⭐ |
| [01_QUICK_REFERENCE.md](01_QUICK_REFERENCE.md) | 快速参考卡，常用命令 | 5分钟 | ⭐⭐⭐⭐ |
| [02_USER_GUIDE.md](02_USER_GUIDE.md) | 完整用户指南，诊断和优化 | 30分钟 | ⭐⭐⭐⭐⭐ |
| [03_ARCHITECTURE.md](03_ARCHITECTURE.md) | 系统架构和开发指南 | 1小时 | ⭐⭐⭐⭐ |
| [04_OPTIMIZATION.md](04_OPTIMIZATION.md) | 代码优化详解 | 30分钟 | ⭐⭐⭐ |
| [05_API_REFERENCE.md](05_API_REFERENCE.md) | API完全参考 | 参考用 | ⭐⭐⭐ |

### experiments/docs/ 目录

| 文件 | 用途 | 阅读时间 | 重要性 |
|------|------|---------|--------|
| [EVALUATION_GUIDE.md](../experiments/docs/EVALUATION_GUIDE.md) | 评估框架技术细节 | 1小时 | ⭐⭐⭐⭐ |

---

## 📖 推荐阅读路径

### 路径A: 我很着急，只想快速验证系统

```
1. START_HERE.md (2分钟)
   └─ 运行评估脚本
   └─ 查看结果

完成！✓
```

### 路径B: 我想全面了解系统

```
1. START_HERE.md (2分钟)
   ↓
2. QUICK_REFERENCE.md (5分钟)
   ↓
3. USER_GUIDE.md (30分钟)
   ├─ 快速启动
   ├─ 理解指标
   ├─ 诊断问题
   └─ 优化建议
   ↓
4. ARCHITECTURE.md (参考用)

完全掌握！✓
```

### 路径C: 我是开发者，想修改和优化代码

```
1. START_HERE.md (2分钟)
   ↓
2. ARCHITECTURE.md (1小时)
   ├─ 系统设计
   ├─ 核心模块
   ├─ 接口定义
   └─ 开发示例
   ↓
3. OPTIMIZATION.md (30分钟)
   └─ 性能优化细节
   ↓
4. API_REFERENCE.md (参考用)
   └─ 接口完全参考

准备好修改代码！✓
```

---

## 🎯 常见问题快速定位

| 问题 | 查看文档 | 部分 |
|------|---------|------|
| 如何快速运行评估？ | START_HERE.md | "立即开始" |
| 什么是路径成功率？ | USER_GUIDE.md | "核心指标说明" |
| 评估结果低怎么办？ | USER_GUIDE.md | "诊断低分原因" |
| 如何优化系统性能？ | USER_GUIDE.md + OPTIMIZATION.md | "优化建议" 和 "性能优化" |
| 如何修改代码？ | ARCHITECTURE.md | "开发指南" |
| KGClient接口有哪些？ | ARCHITECTURE.md 或 API_REFERENCE.md | "核心接口" |
| 如何使用真实HmTest数据？ | USER_GUIDE.md | "使用真实HmTest数据" |
| 评估框架如何工作？ | experiments/docs/EVALUATION_GUIDE.md | 完整指南 |

---

## 📊 文档统计

```
总文档数:       7份 (精简后)
总行数:         ~2000行
推荐首先阅读:   START_HERE.md (2分钟)
最深入的文档:   USER_GUIDE.md (30分钟)
技术参考:       ARCHITECTURE.md + API_REFERENCE.md
```

---

## 🗂️ 目录结构

```
HarmonyOS-App-Testing-Knowledge-Graph/
├── README.md                           ← 项目主文档
├── docs/                               ← 用户和开发者文档
│   ├── INDEX.md                        ← 本文档，导航指南
│   ├── 00_START_HERE.md                ← 快速开始
│   ├── 01_QUICK_REFERENCE.md           ← 快速参考卡
│   ├── 02_USER_GUIDE.md                ← 完整用户指南
│   ├── 03_ARCHITECTURE.md              ← 系统架构
│   ├── 04_OPTIMIZATION.md              ← 性能优化
│   └── 05_API_REFERENCE.md             ← API参考
├── experiments/
│   ├── docs/
│   │   └── EVALUATION_GUIDE.md         ← 评估框架指南
│   ├── standalone_evaluation.py        ← 核心脚本
│   ├── hmtest_synthetic_dataset.py     ← 数据生成器
│   ├── hmtest_synthetic_data/          ← 46条路径
│   └── ...
└── ...
```

---

## ✅ 使用建议

### 首次使用
1. ✅ 读 [00_START_HERE.md](00_START_HERE.md)
2. ✅ 运行评估脚本
3. ✅ 查看 `evaluation_results.json`

### 遇到问题
1. ✅ 查看本 INDEX.md 定位问题
2. ✅ 跳转到相应文档查阅
3. ✅ 按照诊断步骤排查

### 深入学习
1. ✅ 按推荐路径 B 或 C 阅读
2. ✅ 查阅 ARCHITECTURE.md 理解设计
3. ✅ 参考 API_REFERENCE.md 了解接口

---

## 🎉 快速导航

- 🚀 **着急?** → [START_HERE.md](00_START_HERE.md)
- 📖 **学习?** → [USER_GUIDE.md](02_USER_GUIDE.md)
- 🏗️ **开发?** → [ARCHITECTURE.md](03_ARCHITECTURE.md)
- ⚡ **优化?** → [OPTIMIZATION.md](04_OPTIMIZATION.md)
- 🔌 **API?** → [API_REFERENCE.md](05_API_REFERENCE.md)
- 🔬 **评估?** → [EVALUATION_GUIDE.md](../experiments/docs/EVALUATION_GUIDE.md)

---

**最后更新**: 2026-02-15
**文档版本**: 1.0 (精简版)
**推荐优先阅读**: [00_START_HERE.md](00_START_HERE.md)
