# HarmonyOS App Testing Knowledge Graph

鸿蒙系统App自动化测试知识图谱系统

一个基于知识图谱的App自动化测试辅助系统，通过构建App页面转换图谱和意图-路径映射，为GUI Agent提供智能路径规划和操作推荐。

## 📁 项目结构

```
harmonyos_kg/
├── config/
│   └── config.yaml              # 配置文件（数据库、模型、API等）
│
├── kg_core/                     # 核心模块
│   ├── schema.py                # 实体和关系定义（Page, Widget, Transition, Intent等）
│   ├── graph_store.py           # 图数据库操作（支持Neo4j和内存模式）
│   ├── vector_store.py          # 向量数据库操作（支持Milvus和内存模式）
│   └── embeddings.py            # 嵌入模型封装（文本/图像嵌入）
│
├── kg_builder/                  # 图谱构建模块
│   └── graph_builder.py         # 图谱构建器（页面添加、关系建立）
│
├── kg_query/                    # 查询模块
│   ├── path_finder.py           # 路径查询（基于意图查找操作路径）
│   ├── page_matcher.py          # 页面匹配（UI树/标题匹配）
│   └── rag_engine.py            # RAG引擎（检索增强生成）
│
├── agent_interface/             # Agent对接层 ⭐
│   └── kg_client.py             # KGClient（GUI Agent统一接口）
│
├── api/                         # REST API服务
│   └── routes.py                # FastAPI路由（包含请求/响应模型）
│
├── examples/                    # 示例代码
│   ├── demo_build_graph.py      # 构建图谱示例
│   └── demo_with_agent.py       # Agent对接示例
│
├── requirements.txt             # Python依赖
├── README.md                    # 项目说明（本文件）
└── QUICKSTART.md                # 快速开始指南
```

## 🎯 核心功能

### 1. 知识图谱构建
- **页面节点管理**：记录App页面及其属性（类型、标题、描述、意图等）
- **转换关系建模**：记录页面间的转换路径和触发操作
- **意图注册**：将用户意图与目标页面/路径关联

### 2. 智能路径查询
- **意图到路径**：根据用户意图（如"点外卖"）查找操作路径
- **下一步推荐**：基于当前页面和意图推荐下一步操作
- **路径优化**：考虑成功率、步骤数等因素选择最优路径

### 3. 页面匹配
- **UI树匹配**：基于UI层次结构匹配当前页面
- **语义匹配**：使用向量相似度匹配页面

### 4. RAG增强
- **上下文检索**：为LLM决策提供相关页面和操作信息
- **提示词生成**：自动生成包含图谱知识的提示词

## 🚀 知识图谱为GUI测试Agent带来的提升

### 1. **从"盲目探索"到"智能导航"**

**传统Agent的痛点**：
- 需要大量试错才能找到目标页面
- 每一步都要重新分析UI，决策成本高
- 容易陷入死循环或无效路径

**知识图谱的解决方案**：
```python
# Agent只需提供意图，图谱直接返回完整路径
result = kg.query_path("com.meituan.app", "点外卖")
# 返回: 首页 → 外卖频道 → 商家列表 → 商家详情 → 加入购物车
```

**预期效果**：
- 减少盲目探索步骤：基于历史路径直接导航
- 避免无效操作：基于成功率统计过滤低效路径
- 减少重复决策：已知路径无需每步调用 LLM

---

### 2. **从"单次决策"到"全局规划"**

**传统Agent的局限**：
- 只能看到当前页面，缺乏全局视野
- 无法预知操作后果，容易走弯路
- 遇到异常页面时不知所措

**知识图谱的优势**：
```python
# 图谱提供全局视图和备选方案
result = kg.query_path("com.meituan.app", "点外卖")
if result["success"]:
    # 主路径
    execute_path(result["path"])
    # 如果失败，自动尝试备选路径
    for alt_path in result["alternatives"]:
        if try_path(alt_path):
            break
```

**预期效果**：
- 一次查询获得完整操作序列，而非逐步决策
- 提供备选路径，主路径失败时可自动切换
- 基于历史成功率选择路径

---

### 3. **从"静态规则"到"持续学习"**

**传统Agent的问题**：
- 规则硬编码，难以适应App更新
- 新功能需要人工编写测试脚本
- 无法从失败中学习

**知识图谱的学习能力**：
```python
# Agent执行操作后上报结果，图谱自动学习
kg.report_transition(
    from_page="home",
    action={"type": "click", "widget": "food_btn"},
    to_page="food_list",
    success=True,
    latency_ms=500
)
# 图谱更新：记录成功路径，更新统计信息
```

**预期效果**：
- App 更新后，图谱通过新的运行数据自动学习新路径
- 每次测试都增强图谱知识，跨运行积累经验
- 记录失败路径和成功率，避免重复错误

---

### 4. **从"UI匹配困难"到"智能页面识别"**

**传统Agent的挑战**：
- UI元素ID变化导致定位失败
- 动态内容导致页面识别困难
- 相似页面难以区分

**知识图谱的解决方案**：
```python
# 多维度页面匹配
page_info = kg.match_current_page(
    app_id="com.meituan.app",
    ui_hierarchy=current_ui_tree,  # UI树结构
    page_title="首页"              # 页面标题
)
# 图谱结合：UI结构 + 语义描述 + 历史路径
```

**预期效果**：
- 结合结构指纹、语义向量、标题多维度匹配，提升匹配鲁棒性
- 忽略动态内容变化（列表数据、时间、电量），UI 更新时仍能识别页面
- Jaccard 模糊匹配容忍小版本控件调整

---

### 5. **从"LLM调用昂贵"到"RAG增强决策"**

**传统Agent的成本**：
- 每步都要调用LLM，成本高、延迟大
- LLM缺乏App特定知识，容易产生错误决策
- 提示词需要人工编写，难以维护

**知识图谱的RAG能力**：
```python
# 为LLM提供结构化上下文
context = kg.get_rag_context(
    app_id="com.meituan.app",
    query="点外卖",
    current_page="home"
)
# 返回包含相关页面、操作路径、历史经验的提示词
llm_prompt = context["prompt"]
# LLM基于图谱知识做出更准确的决策
```

**预期效果**：
- 已知路径可直接由图谱提供，减少 LLM 调用
- LLM 获得结构化的导航知识（成功率、目标页面），减少幻觉
- 本地图谱查询延迟远低于远程 LLM 推理

---

### 6. **从"难以调试"到"可解释路径"**

**传统Agent的痛点**：
- 失败时难以定位问题
- 无法解释为什么选择某个操作
- 调试需要大量日志分析

**知识图谱的可解释性**：
```python
result = kg.query_path("com.meituan.app", "点外卖")
# 返回的路径包含：
# - 每个步骤的置信度
# - 历史成功率
# - 备选方案
# - 失败原因（如果有）
```

**提升效果**：
- 🔍 **问题定位快速**：失败时直接查看路径置信度和历史统计
- 📝 **测试报告自动生成**：基于图谱生成可读的操作序列
- 🐛 **调试效率提升**：可视化图谱结构，直观理解Agent行为

---

### 7. **从"单App测试"到"跨App知识复用"**

**知识图谱的扩展能力**：
- 不同App的相似功能可以共享知识（如"搜索"功能）
- 新App可以快速迁移已有图谱知识
- 跨App的模式识别（如"登录流程"）

---

---

## 💡 典型应用场景

### 场景1: 回归测试自动化
```python
# 传统方式：需要为每个测试用例编写脚本
# 使用图谱：只需提供意图，自动生成测试路径
test_cases = ["点外卖", "查看订单", "申请退款"]
for intent in test_cases:
    path = kg.query_path(app_id, intent)
    execute_test(path)
```

### 场景2: 探索性测试
```python
# Agent探索新功能时，图谱提供相似功能的参考路径
new_feature = "直播购物"
similar_intents = kg.find_similar_intents(new_feature)
# 基于相似意图的路径，快速理解新功能
```

### 场景3: 异常恢复
```python
# 遇到未知页面时，图谱帮助定位
unknown_page = detect_current_page()
matched = kg.match_current_page(ui_hierarchy=unknown_page)
if matched:
    # 找到匹配页面，获取可用操作
    actions = kg.get_available_actions(matched.page_id)
```

---

## 🎓 总结

知识图谱系统为 GUI 测试 Agent 带来的核心价值：

1. **智能导航**：从盲目探索到基于历史路径的导航
2. **全局规划**：从逐步决策到基于意图的全局路径规划
3. **持续学习**：每次运行自动积累页面、转换、成功率数据
4. **稳定匹配**：结构指纹忽略动态内容，跨运行稳定识别页面
5. **可解释性**：每条路径都有成功率、步骤数、置信度等可审查数据

## 🔗 与 GUI Agent 的实际对接

本知识图谱已与 [utg-guided-gui-agent](../utg-guided-gui-agent/) 项目中的 Mobile-Agent-v3 完成深度整合，作为 Agent 的**唯一导航知识系统**（取代了原有的 AppGraph 和 UTG 两套独立系统）。

### 为什么需要整合？

原系统存在三套相互独立的导航知识机制：

| 系统 | 定位 | 局限性 |
|------|------|--------|
| **UTG** (UI Transition Graph) | 状态级转换图，记录 UI 元素哈希 → 下一状态 | 状态哈希对任何微小 UI 变化都敏感，难以跨运行复用 |
| **AppGraph** | 页面级导航图，基于控件树结构指纹 | 纯结构匹配，无语义理解，无意图规划能力 |
| **KG** (本项目) | 语义知识图谱，支持意图推理和路径规划 | 原始页面匹配过于粗糙（仅用 widget type 的 Jaccard），实际匹配率低 |

三者在 Agent 中互斥使用（`if app_graph ... elif bridge ... elif utg`），无法取长补短。

**整合后**：将 AppGraph 的结构指纹匹配能力和 Widget 级别转换追踪整合进 KG，统一为一套系统，同时保留 KG 原有的语义搜索和意图规划能力。

### 对接架构

Agent 通过 `BridgeAdapter` 在每个 step 循环中与 KG 交互：

```
Mobile-Agent-v3 step() 循环
    │
    │ ① 任务开始 (step_idx == 0)
    ├─→ bridge.plan_task(intent, state)
    │       └─ KGClient.query_path()
    │       └─ 返回宏观路径: HomePage → Settings → Network → WiFi Toggle
    │
    │ ② 每步执行前
    ├─→ bridge.get_combined_hint(goal, state)
    │       ├─ _match_page(state)          # 用结构指纹匹配当前页面
    │       ├─ format_kg_direction()        # 宏观路径方向提示
    │       ├─ format_navigation_hint()     # 已知动作 + 历史成功率
    │       └─ format_exploration_hint()    # 未探索控件列表
    │       → 注入到 Executor 的 LLM prompt 中
    │
    │ ③ 每步执行后
    └─→ bridge.report_transition(state_before, action, state_after, outcome)
            ├─ _ensure_page_registered()   # 新页面自动注册
            ├─ find_trigger_widget()        # 识别触发控件
            ├─ kg.report_transition()       # 记录带 widget 详情的转换
            └─ save_to_json()               # 持久化到 kg_graph.json
```

**关键交互接口**：

```python
# BridgeAdapter 对 KGClient 的调用
kg.query_path(app_id, intent, current_page)    # 宏观路径规划
kg.match_current_page(app_id, ui_hierarchy, page_title)  # 页面匹配
kg.report_transition(from_page, action, to_page, success)  # 转换上报
kg.add_page(app_id, page_name, page_type, description)    # 页面注册
```

### 结构指纹匹配：原理与实际作用

#### 问题背景

在 Android 的 Accessibility 树中，许多 App 的列表项和菜单项是**复合容器控件**：外层是一个可点击的 `LinearLayout`，内层包含图标 `ImageView` 和文字 `TextView`。例如，Settings 页面的 UI 树长这样：

```
LinearLayout (clickable, text=空)           ← 容器，没有 text
  ├─ ImageView (icon)
  └─ LinearLayout
       ├─ TextView (text="Network & internet")  ← 文字在子节点里
       └─ TextView (text="Mobile, Wi-Fi, hotspot")
```

**原始 state_hash 的问题**：对整个 UI 树做 JSON 序列化后取 MD5。任何动态内容变化（列表滚动、时间更新、电池百分比）都会改变哈希，导致同一页面被识别为不同页面。

**原始 Jaccard 匹配的问题**：只比较 `WidgetType` 枚举值（如 "button"、"text"），粒度太粗——大多数页面都有 button 和 text，区分度极低。

#### 结构指纹的设计

```python
Page.compute_structural_fingerprint(app_id, activity, widgets_data)
```

**核心思路**：只用 `class_name` + `resource_id` 的组合作为特征，**忽略 text（动态内容）和 bounds（布局微调）**。

```python
# 实际计算过程
structural_features = sorted(set(
    f"{w['class_name']}|{w['resource_id']}"
    for w in widgets_data
    if w.get("resource_id")   # 只保留有 resource_id 的控件
))
fingerprint = md5(f"{app_id}:{activity}:{','.join(structural_features)}")[:16]
```

**为什么这样设计**：
- `resource_id` 是开发者在代码中定义的控件标识符（如 `network_item`、`search_bar`），在同一版本 App 中保持不变
- `class_name` 表示控件类型（如 `LinearLayout`、`RecyclerView`），是结构性的
- 而 `text` 是运行时动态填充的（"47% used"、"3 new messages"），不稳定
- `bounds` 受屏幕尺寸和内容多少影响，不稳定

**实际效果示例**：Settings 页面不管 WiFi 是开还是关、电池是 50% 还是 100%、存储用了多少，只要菜单项的 resource_id 结构不变，指纹就相同。

#### 三级匹配策略

```
PageMatcher.match_page()
    │
    ├─ 第1级：结构指纹精确匹配 (confidence=1.0)
    │   structural_fingerprint 完全相同
    │   → 复杂度 O(n)，n=同 app 的已知页面数
    │
    ├─ 第2级：Jaccard 模糊匹配 (threshold≥0.7)
    │   class_name|resource_id 集合的交并比
    │   同 activity 加 0.1 bonus
    │   → 用于处理 App 小版本更新导致的控件微调
    │
    └─ 第3级：语义向量匹配 (threshold≥0.6)
        基于 sentence-transformer 的文本嵌入
        → 用于跨版本或跨设备的泛化匹配
```

#### 对比其他方案

| 方案 | 稳定性 | 区分度 | 语义能力 | 是否需要预训练 |
|------|--------|--------|----------|----------------|
| 像素哈希 (screenshot MD5) | 极低（任何渲染变化） | 高 | 无 | 否 |
| UI 树 JSON 哈希 (state_hash) | 低（动态内容敏感） | 高 | 无 | 否 |
| Widget type Jaccard (原 KG) | 高（太粗粒度） | 低 | 无 | 否 |
| **结构指纹 (本方案)** | **高（忽略动态内容）** | **高（resource_id 区分）** | 无 | 否 |
| 语义向量匹配 | 中 | 中 | **有** | 是 |
| **三级融合 (本方案最终)** | **高** | **高** | **有** | 部分 |

### 导航提示的实际注入

当 KG 中已积累足够数据时，Agent 的 Executor LLM 在每步决策前会收到如下格式的导航提示（直接拼接在 prompt 末尾）：

```
[App Navigation Knowledge Graph]
Current page: Settings (depth: 0, visited: 3 times)

Known actions from this page (5 total):
  1. Click "Network & internet" [network_item] (LinearLayout) at (540, 300)
     -> NetworkSettings (success: 8/10, 80%)
  2. Click "Connected devices" [bt_item] (LinearLayout) at (540, 450)
     -> BluetoothSettings (success: 5/5, 100%)
  3. Click "Apps" [apps_item] (LinearLayout) at (540, 600)
     -> AppsPage (success: 3/4, 75%)

[Exploration Opportunity] 2 unexplored clickable widgets:
  1. Accessibility at (540, 900) (LinearLayout)
  2. About phone at (540, 1050) (LinearLayout)
```

**这个提示解决的具体问题**：

许多 Android 页面的 Accessibility 树中，容器控件（如 `LinearLayout`）是可点击的但没有 `text` 属性——文字在其子节点 `TextView` 中。LLM 看到截图上有 "Network & internet" 文字，但 UI 元素列表中只有一排没有文字的 `LinearLayout`，无法将视觉看到的文字与可操作的元素对应起来。导航提示通过历史转换记录补充了这个关键的映射关系。

### Widget 级别的转换数据

每次 Agent 执行动作后，BridgeAdapter 自动提取并记录完整的控件信息：

```python
# bridge.report_transition() 实际记录到 KG 的数据
Transition(
    source_page_id="a1b2c3d4...",       # 结构指纹生成的页面 ID
    target_page_id="e5f6g7h8...",
    action_type=ActionType.CLICK,
    trigger_widget_text="Network & internet",   # 控件显示文字
    trigger_widget_class="LinearLayout",         # Android 控件类名
    trigger_widget_resource_id="network_item",   # 开发者定义的 resource_id
    trigger_widget_center=(540, 300),            # 屏幕上的像素坐标
    input_text="",                               # INPUT 类型时记录输入内容
    success_count=8, fail_count=2,               # 跨运行累积的成功/失败计数
)
```

**控件识别方法**：通过 `find_trigger_widget()` 函数，根据 action 中的 (x, y) 坐标，在当前页面的所有 widget 中找到面积最小的包含该坐标的控件——这就是触发转换的控件。

### 增量学习与数据持久化

KG 在 Agent 运行过程中**边跑边学**：

1. **自动页面注册**：`_ensure_page_registered()` 在 `_match_page()` 匹配失败时自动触发，计算结构指纹后注册新页面
2. **转换记录聚合**：同一页面间同一控件的重复转换不会创建新记录，而是更新已有记录的 `success_count` / `fail_count`
3. **JSON 持久化**：每次 `report_transition()` 后自动调用 `save_to_json(kg_persist_path)`，确保数据不丢失
4. **跨运行积累**：下次启动 Agent 时，`BridgeAdapter.__init__()` 自动调用 `load_from_json()` 加载已有数据

### 运行命令

```bash
cd utg-guided-gui-agent/gui_agent/MobileAgent/Mobile-Agent-v3/android_world_v3

python run_ma3.py \
  --suite_family=android_world \
  --tasks=SystemWifiTurnOnVerify \
  --agent_name=mobile_agent_v3 \
  --model=gui-owl-7b \
  --api_key=EMPTY \
  --base_url=http://127.0.0.1:8000/v1 \
  --use_kg=True \
  --kg_project_path=/path/to/HarmonyOS-App-Testing-Knowledge-Graph \
  --fusion_mode=both
```

### 关键文件

**KG 本体**（本项目）：

| 文件 | 说明 |
|------|------|
| `kg_core/schema.py` | 数据模型：Page（含 structural_fingerprint、activity、widgets）、Transition（含 trigger_widget_class/resource_id/center）、Widget、Intent |
| `kg_core/graph_store.py` | 图存储：JSON 持久化（save_to_json / load_from_json）、结构指纹查询（find_page_by_fingerprint）、转换匹配（find_matching_transition） |
| `kg_query/page_matcher.py` | 三级页面匹配：结构指纹精确匹配 → Jaccard 模糊匹配 → 语义向量匹配 |
| `agent_interface/kg_client.py` | Agent 统一接口：query_path、match_current_page、report_transition、add_page |

**Bridge 层**（位于 `android_world_v3/android_world/bridge/`）：

| 文件 | 说明 |
|------|------|
| `adapter.py` | 核心协调器：plan_task（宏观规划）、get_combined_hint（生成提示）、report_transition（双向回馈 + 自动页面注册 + 持久化） |
| `hint_formatter.py` | 提示格式化：format_navigation_hint（已知动作 + 成功率）、format_exploration_hint（未探索控件）、format_kg_direction（宏观路径方向） |
| `page_abstractor.py` | State 转换工具：state_to_widget_list（提取完整控件列表）、find_trigger_widget（坐标定位触发控件）、detect_app_id、extract_page_title |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**核心依赖**：
- `networkx` - 内存图数据库（Demo模式）
- `numpy` - 向量计算
- `pydantic` - 数据验证
- `sentence-transformers` - 文本嵌入（可选）
- `fastapi` + `uvicorn` - API服务（可选）
- `neo4j` - 图数据库（生产模式，可选）

### 2. 配置

编辑 `config/config.yaml`：

```yaml
# 运行模式: memory（内存模式，用于Demo）| production（生产模式）
mode: memory

# 图数据库配置
graph_db:
  type: memory  # neo4j | memory

# 向量数据库配置
vector_db:
  type: memory  # milvus | memory
```

### 3. 运行示例

```bash
# 构建图谱示例
python examples/demo_build_graph.py

# Agent对接示例
python examples/demo_with_agent.py
```

## 🔌 与GUI Agent对接

### 方式1: 直接使用KGClient（推荐）

```python
from agent_interface.kg_client import KGClient

# 初始化客户端
kg = KGClient()

# 1. 查询完整操作路径
result = kg.query_path(
    app_id="com.meituan.app",
    intent="点外卖",
    current_page="home_page_id",
    max_steps=10
)

if result["success"]:
    for step in result["path"]["steps"]:
        # step包含: action, widget_id, widget_text, expected_page
        execute_action(step["action"], step["widget_id"])

# 2. 获取下一步操作（实时模式）
action = kg.get_next_action(
    current_page="current_page_id",
    intent="点外卖",
    app_id="com.meituan.app"
)
if action:
    execute_action(action.action_type, action.widget_id)

# 3. 匹配当前页面
page_info = kg.match_current_page(
    app_id="com.meituan.app",
    ui_hierarchy={"widgets": [...]},  # UI树结构
    page_title="首页"
)

# 4. 上报执行结果（图谱学习）
kg.report_transition(
    from_page="page_a",
    action={"type": "click", "widget": "btn_id"},
    to_page="page_b",
    success=True,
    latency_ms=500
)

# 5. 获取RAG上下文（供LLM决策）
context = kg.get_rag_context(
    app_id="com.meituan.app",
    query="点外卖",
    current_page="home_page_id"
)
llm_prompt = context["prompt"]  # 直接传给LLM
```

### 方式2: REST API调用

```bash
# 启动API服务
python -m api.routes

# 查询路径
curl -X POST http://localhost:8000/api/v1/query/path \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "com.meituan.app",
    "intent": "点外卖",
    "current_page_id": "home_page_id"
  }'

# 获取下一步操作
curl -X POST http://localhost:8000/api/v1/query/next-action \
  -H "Content-Type: application/json" \
  -d '{
    "current_page_id": "current_page_id",
    "intent": "点外卖",
    "app_id": "com.meituan.app"
  }'

# 查看API文档
# 访问 http://localhost:8000/docs
```

## 📊 核心数据模型

### 实体类型
- **App**: 应用（app_id, app_name, version）
- **Page**: 页面（page_id, page_name, page_type, description, intents）
- **Widget**: 控件（widget_id, widget_type, text, xpath, bounds）
- **Intent**: 意图（intent_id, intent_text, keywords）
- **ActionPath**: 操作路径（path_id, steps, confidence）

### 关系类型
- **TRANSITIONS_TO**: 页面转换（source_page → target_page，包含触发操作）
- **ACHIEVES_INTENT**: 实现意图（ActionPath → Intent）

## 🔄 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                       GUI Agent                              │
├─────────────────────────────────────────────────────────────┤
│  1. 接收测试任务: "点外卖"                                    │
│  2. 获取当前页面状态 (UI树/截图)                              │
│  3. 调用 kg.query_path() 获取操作路径                        │
│  4. 逐步执行操作:                                            │
│     - 执行 step["action"] on step["widget_id"]             │
│     - 调用 kg.report_transition() 上报结果                  │
│  5. 任务完成                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    KGClient (对接层)                         │
├─────────────────────────────────────────────────────────────┤
│  • query_path()      → PathFinder.find_path_by_intent()    │
│  • get_next_action() → PathFinder.get_next_action()        │
│  • match_current_page() → PageMatcher.match()              │
│  • get_rag_context() → RAGEngine.retrieve()                │
│  • report_transition() → GraphStore.update_transition()     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      存储层                                  │
├─────────────────────────────────────────────────────────────┤
│  GraphStore (NetworkX/Neo4j)  │  VectorStore (NumPy/Milvus) │
│  • 页面节点                  │  • 页面向量                  │
│  • 转换边                    │  • 意图向量                  │
└─────────────────────────────────────────────────────────────┘
```

## 📖 核心接口说明

| 方法                                       | 用途             | 返回      |
| ------------------------------------------ | ---------------- | --------- |
| `query_path(app_id, intent, current_page)` | 查询完整操作路径 | 步骤序列  |
| `get_next_action(current_page, intent)`    | 获取下一步操作   | 单个操作  |
| `match_current_page(app_id, ui_hierarchy)` | 匹配当前页面     | 页面ID    |
| `report_transition(from, action, to)`      | 上报转换结果     | -         |
| `get_rag_context(app_id, query)`           | 获取RAG上下文    | LLM提示词 |
| `add_page(app_id, page_name, ...)`         | 添加页面         | 页面ID    |
| `register_intent(app_id, intent_text)`     | 注册意图         | 意图ID    |

## 🛠️ 开发模式

### 内存模式（Demo/开发）
- 使用 `NetworkX` 作为内存图数据库
- 使用 `NumPy` 数组存储向量
- 无需外部数据库，适合快速开发和测试

### 生产模式
- 使用 `Neo4j` 作为图数据库
- 使用 `Milvus` 作为向量数据库
- 支持持久化存储和分布式部署

## 📚 完整文档

所有文档已按类别整理到 [docs/](docs/) 目录。查看 [docs/INDEX.md](docs/INDEX.md) 获取完整导航。

### 快速导航

- 🚀 **快速开始** → [docs/00_START_HERE.md](docs/00_START_HERE.md) (2分钟)
- 📖 **用户指南** → [docs/02_USER_GUIDE.md](docs/02_USER_GUIDE.md) (30分钟)
- 🏗️ **系统架构** → [docs/03_ARCHITECTURE.md](docs/03_ARCHITECTURE.md) (开发者必读)
- ⚡ **性能优化** → [docs/04_OPTIMIZATION.md](docs/04_OPTIMIZATION.md) (优化参考)
- 🔌 **API参考** → [docs/05_API_REFERENCE.md](docs/05_API_REFERENCE.md) (API集成)
- 🔬 **评估框架** → [experiments/docs/EVALUATION_GUIDE.md](experiments/docs/EVALUATION_GUIDE.md) (技术细节)

### 文档系统

```
docs/
├── INDEX.md                    ← 文档导航总览
├── 00_START_HERE.md            ← 快速开始指南
├── 01_QUICK_REFERENCE.md       ← 快速参考卡
├── 02_USER_GUIDE.md            ← 完整用户指南
├── 03_ARCHITECTURE.md          ← 系统架构和开发指南
├── 04_OPTIMIZATION.md          ← 代码优化说明
└── 05_API_REFERENCE.md         ← API完全参考

experiments/docs/
└── EVALUATION_GUIDE.md         ← 评估框架指南
```
