# 🚀 快速开始指南

## 一、项目结构

```
harmonyos_kg/
├── kg_core/                # 核心模块
│   ├── schema.py           # 实体定义 (Page, Widget, Transition, Intent)
│   ├── graph_store.py      # 图存储 (NetworkX内存图)
│   ├── vector_store.py     # 向量存储 (NumPy内存向量)
│   └── embeddings.py       # 嵌入模型
├── kg_query/               # 查询模块
│   ├── path_finder.py      # 路径查询
│   ├── page_matcher.py     # 页面匹配
│   └── rag_engine.py       # RAG引擎
├── kg_builder/             # 构建模块
│   └── graph_builder.py    # 图谱构建器
├── agent_interface/        # Agent对接层 ⭐
│   └── kg_client.py        # KGClient (核心对接接口)
├── api/                    # REST API
│   └── routes.py           # FastAPI服务
└── examples/               # 示例代码
    ├── demo_build_graph.py # 构建图谱示例
    └── demo_with_agent.py  # Agent对接示例
```

## 二、与GUI Agent对接

### 方式1: 直接使用KGClient (推荐)

```python
from agent_interface import KGClient

# 初始化
kg = KGClient()

# ===== Agent查询路径 =====
result = kg.query_path(
    app_id="com.meituan.app",
    intent="点外卖",
    current_page="home_page_id"
)

if result["success"]:
    for step in result["path"]["steps"]:
        # step包含: action, widget_id, widget_text, expected_page
        execute_action(step["action"], step["widget_id"])

# ===== 获取下一步操作 (实时模式) =====
action = kg.get_next_action(
    current_page="current_page_id",
    intent="点外卖"
)
if action:
    execute_action(action.action_type, action.widget_id)

# ===== 上报执行结果 (图谱学习) =====
kg.report_transition(
    from_page="page_a",
    action={"type": "click", "widget": "btn_id"},
    to_page="page_b",
    success=True
)

# ===== 获取RAG上下文 (供LLM决策) =====
context = kg.get_rag_context(
    app_id="com.meituan.app",
    query="点外卖",
    current_page="home_page_id"
)
llm_prompt = context["prompt"]  # 直接传给LLM
```

### 方式2: REST API调用

```bash
# 启动服务
pip install fastapi uvicorn
python -m api.routes

# 查询路径
curl -X POST http://localhost:8000/api/v1/query/path \
  -H "Content-Type: application/json" \
  -d '{"app_id": "com.meituan.app", "intent": "点外卖"}'
```

## 三、核心接口说明

| 方法                                       | 用途             | 返回      |
| ------------------------------------------ | ---------------- | --------- |
| `query_path(app_id, intent, current_page)` | 查询完整操作路径 | 步骤序列  |
| `get_next_action(current_page, intent)`    | 获取下一步操作   | 单个操作  |
| `match_current_page(app_id, ui_hierarchy)` | 匹配当前页面     | 页面ID    |
| `report_transition(from, action, to)`      | 上报转换结果     | -         |
| `get_rag_context(app_id, query)`           | 获取RAG上下文    | LLM提示词 |
| `add_page(app_id, page_name, ...)`         | 添加页面         | 页面ID    |
| `register_intent(app_id, intent_text)`     | 注册意图         | 意图ID    |

## 四、对接流程图

```
┌─────────────────────────────────────────────────────────────┐
│                      你的 GUI Agent                          │
├─────────────────────────────────────────────────────────────┤
│  1. 接收测试任务: "点外卖"                                    │
│  2. 获取当前页面状态 (UI树/截图)                              │
│  3. 调用 kg.query_path() 获取操作路径                        │
│  4. 逐步执行:                                                │
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
│  • get_rag_context() → RAGEngine.retrieve()                │
│  • report_transition()→ GraphStore.update_transition()     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      存储层                                  │
├─────────────────────────────────────────────────────────────┤
│  GraphStore (NetworkX)  │  VectorStore (NumPy)             │
│  • 页面节点             │  • 页面向量                       │
│  • 转换边               │  • 意图向量                       │
└─────────────────────────────────────────────────────────────┘
```

## 五、运行Demo

```bash
cd harmonyos_kg

# 安装依赖 (仅需networkx和numpy)
pip install networkx numpy pydantic

# 运行构建Demo
python examples/demo_build_graph.py

# 运行Agent对接Demo
python examples/demo_with_agent.py
```

## 六、在你的Agent中集成

```python
# your_agent.py
from agent_interface import KGClient

class YourGUIAgent:
    def __init__(self):
        self.kg = KGClient()
    
    def run_task(self, task: str):
        # 获取当前页面
        current_page = self.detect_current_page()
        
        # 查询路径
        result = self.kg.query_path("com.meituan.app", task, current_page)
        
        if not result["success"]:
            return self.handle_error()
        
        # 执行每一步
        for step in result["path"]["steps"]:
            widget = self.find_widget(step["widget_text"])
            success = self.click(widget)
            
            # 上报结果
            self.kg.report_transition(
                from_page=current_page,
                action={"type": step["action"], "widget": step["widget_id"]},
                to_page=step["expected_page"],
                success=success
            )
            
            current_page = step["expected_page"]
```
