# 知识图谱系统接口规范

本文档定义了HarmonyOS App自动化测试知识图谱系统的所有接口，包括输入参数、主要行为和输出格式。

## 设计原则

1. **输入合理性**：接口输入要求最小化，避免要求过多信息
2. **行为明确**：每个接口的行为清晰可预测
3. **输出结构化**：返回结果采用统一的结构化格式
4. **容错性**：接口应能处理异常情况并返回明确的错误信息

---

## 一、核心查询接口

### 1.1 查询操作路径 (`query_path`)

**解决痛点**：从"盲目探索"到"智能导航"，从"单次决策"到"全局规划"

**接口说明**：根据用户意图查询从当前页面到目标页面的完整操作路径，支持全局路径规划。

**输入参数**：
```python
{
    "app_id": str,              # 必需，应用ID，如 "com.meituan.app"
    "intent": str,              # 必需，用户意图的自然语言描述，如 "点外卖"、"查找附近餐厅"
    "current_page": str,        # 可选，当前页面ID，如果不提供则从应用首页开始
    "max_steps": int            # 可选，最大步骤数限制，默认10
}
```

**主要行为**：
1. 通过向量相似度匹配意图，找到目标页面
2. 在图谱中查找从当前页面到目标页面的最短路径
3. 考虑路径的成功率、步骤数等因素，选择最优路径
4. 如果存在多条可行路径，返回主路径和备选路径
5. 为每个步骤计算置信度和历史成功率

**输出格式**：
```python
{
    "success": bool,            # 是否成功找到路径
    "message": str,             # 成功或失败的消息说明
    "confidence": float,        # 整体路径置信度 (0.0-1.0)
    "path": {                   # 主路径（当success=True时存在）
        "total_steps": int,     # 总步骤数
        "estimated_time_ms": int, # 预估耗时（毫秒）
        "steps": [              # 操作步骤序列
            {
                "step": int,                    # 步骤序号（从1开始）
                "action_type": str,             # 操作类型：click, input, swipe, back等
                "widget_id": str,               # 目标控件ID（如果已知）
                "widget_text": str,             # 目标控件文本（用于定位）
                "widget_xpath": str,            # 控件XPath（如果可用）
                "input_text": str,              # 输入文本（仅input类型需要）
                "expected_page": str,           # 预期到达的页面ID
                "expected_page_name": str,      # 预期页面名称
                "confidence": float,            # 该步骤的置信度
                "success_rate": float,          # 历史成功率
                "description": str              # 步骤描述，如 "点击'外卖'按钮，进入外卖首页"
            }
        ]
    },
    "alternatives": [           # 备选路径列表（可选）
        {
            "total_steps": int,
            "confidence": float,
            "steps": [...],
            "reason": str       # 备选原因，如 "路径更短但成功率较低"
        }
    ],
    "target_page": {            # 目标页面信息（当success=True时存在）
        "page_id": str,
        "page_name": str,
        "page_type": str,
        "description": str
    }
}
```

**失败情况**：
- `success=False`，`message` 包含失败原因，如：
  - "未找到匹配的意图"
  - "当前页面不在图谱中"
  - "无法找到从当前页面到目标页面的路径"
  - "路径步骤数超过限制"

---

### 1.2 获取下一步操作 (`get_next_action`)

**解决痛点**：从"单次决策"到"智能导航"，减少LLM调用

**接口说明**：基于当前页面和意图，返回立即需要执行的下一个操作。适用于实时决策场景。

**输入参数**：
```python
{
    "current_page": str,        # 必需，当前页面ID
    "intent": str,              # 必需，目标意图
    "app_id": str               # 可选，应用ID（用于验证）
}
```

**主要行为**：
1. 根据意图找到目标页面
2. 查找从当前页面到目标页面的路径
3. 返回路径中的第一个操作步骤
4. 如果当前页面就是目标页面，返回None或特殊标记

**输出格式**：
```python
{
    "action": {                 # 操作信息（如果存在下一步操作）
        "action_type": str,     # click, input, swipe, back等
        "widget_id": str,       # 控件ID
        "widget_text": str,     # 控件文本
        "widget_xpath": str,    # 控件XPath
        "input_text": str,      # 输入文本（仅input类型）
        "confidence": float,    # 置信度
        "expected_page": str,   # 预期到达页面ID
        "description": str      # 操作描述
    },
    "is_complete": bool,        # 是否已到达目标页面
    "remaining_steps": int      # 剩余步骤数（如果未完成）
}
```

**特殊情况**：
- 如果已到达目标页面：`is_complete=True`，`action=None`
- 如果无法找到路径：返回 `{"action": None, "is_complete": False, "error": "错误信息"}`

---

### 1.3 匹配当前页面 (`match_current_page`)

**解决痛点**：从"UI匹配困难"到"智能页面识别"

**接口说明**：根据UI结构、页面标题等信息，匹配图谱中的页面节点。

**输入参数**：
```python
{
    "app_id": str,              # 必需，应用ID
    "ui_hierarchy": dict,       # 可选，UI控件树结构（简化版，包含关键控件信息）
    "page_title": str,          # 可选，页面标题
    "page_screenshot": str      # 可选，页面截图路径或base64（未来扩展）
}
```

**UI Hierarchy 格式（最小化要求）**：
```python
{
    "widgets": [                # 关键控件列表（至少包含可见的主要控件）
        {
            "id": str,          # 控件ID（可选）
            "text": str,        # 控件文本
            "type": str,        # 控件类型：button, text, input等
            "bounds": str       # 控件位置（可选，格式："x1,y1,x2,y2"）
        }
    ],
    "page_structure": str       # 页面结构描述（可选，如"包含搜索框和列表"）
}
```

**主要行为**：
1. 如果提供`page_title`，优先使用标题进行精确匹配
2. 如果提供`ui_hierarchy`，提取关键特征进行结构匹配
3. 使用向量相似度进行语义匹配
4. 结合历史访问路径进行上下文推断
5. 返回匹配度最高的页面及可用操作

**输出格式**：
```python
{
    "matched": bool,            # 是否成功匹配
    "page": {                   # 匹配到的页面信息（当matched=True时）
        "page_id": str,
        "page_name": str,
        "page_type": str,
        "description": str,
        "confidence": float     # 匹配置信度 (0.0-1.0)
    },
    "available_actions": [      # 该页面的可用操作列表
        {
            "action_type": str,
            "widget_id": str,
            "widget_text": str,
            "target_page_id": str,
            "target_page_name": str,
            "success_rate": float
        }
    ],
    "candidates": [             # 候选页面列表（如果匹配度较低）
        {
            "page_id": str,
            "page_name": str,
            "confidence": float
        }
    ]
}
```

**失败情况**：
- `matched=False`，`page=None`，`candidates` 可能包含低置信度的候选页面

---

### 1.4 获取RAG上下文 (`get_rag_context`)

**解决痛点**：从"LLM调用昂贵"到"RAG增强决策"

**接口说明**：为LLM决策提供结构化的上下文信息，减少LLM调用次数并提高决策准确性。

**输入参数**：
```python
{
    "app_id": str,              # 必需，应用ID
    "query": str,               # 必需，查询文本（用户意图或问题）
    "current_page": str         # 可选，当前页面ID
}
```

**主要行为**：
1. 根据查询文本检索相关的页面、操作路径和意图
2. 提取历史成功案例和失败案例
3. 生成结构化的提示词，包含：
   - 相关页面信息
   - 推荐的操作路径
   - 历史经验（成功/失败案例）
   - 注意事项和最佳实践

**输出格式**：
```python
{
    "prompt": str,              # 生成的完整提示词（可直接传给LLM）
    "context": {                # 结构化上下文信息
        "relevant_pages": [     # 相关页面
            {
                "page_id": str,
                "page_name": str,
                "description": str,
                "relevance_score": float
            }
        ],
        "recommended_paths": [  # 推荐路径
            {
                "path_id": str,
                "steps": [...],
                "confidence": float,
                "success_rate": float
            }
        ],
        "historical_cases": {   # 历史案例
            "successful": [     # 成功案例
                {
                    "intent": str,
                    "path": [...],
                    "execution_time_ms": int
                }
            ],
            "failed": [         # 失败案例（用于避免错误）
                {
                    "intent": str,
                    "failed_step": int,
                    "reason": str
                }
            ]
        },
        "tips": [str]           # 注意事项和建议
    },
    "suggested_actions": [      # 建议的操作（如果可以直接推荐）
        {
            "action_type": str,
            "widget_text": str,
            "confidence": float,
            "reason": str
        }
    ]
}
```

---

## 二、图谱更新接口（用于持续学习）

### 2.1 上报页面转换 (`report_transition`)

**解决痛点**：从"静态规则"到"持续学习"

**接口说明**：Agent执行操作后上报结果，用于更新图谱的统计信息和学习新路径。

**输入参数**：
```python
{
    "from_page": str,           # 必需，源页面ID
    "action": {                 # 必需，执行的操作
        "type": str,            # 操作类型：click, input, swipe, back等
        "widget": str,          # 控件ID（可选）
        "widget_text": str,     # 控件文本（可选）
        "input_text": str       # 输入文本（仅input类型需要）
    },
    "to_page": str,             # 必需，目标页面ID（执行操作后到达的页面）
    "success": bool,            # 必需，操作是否成功
    "latency_ms": int           # 可选，操作耗时（毫秒）
}
```

**主要行为**：
1. 查找或创建页面转换关系
2. 更新转换的成功/失败统计
3. 更新平均耗时
4. 如果转换不存在，自动创建新的转换边
5. 如果操作失败，记录失败原因（如果提供）

**输出格式**：
```python
{
    "success": bool,            # 上报是否成功
    "transition_id": str,       # 转换关系ID
    "updated": bool,            # 是否为更新已有转换（False表示新建）
    "stats": {                  # 更新后的统计信息
        "success_count": int,
        "fail_count": int,
        "success_rate": float,
        "avg_latency_ms": float
    }
}
```

---

### 2.2 添加页面 (`add_page`)

**解决痛点**：从"静态规则"到"持续学习"，支持动态发现新页面

**接口说明**：将新发现的页面添加到图谱中。

**输入参数**：
```python
{
    "app_id": str,              # 必需，应用ID
    "page_name": str,           # 必需，页面名称
    "page_type": str,           # 可选，页面类型：home, list, detail, form, search, other（默认other）
    "description": str,         # 可选，页面描述
    "intents": [str],           # 可选，该页面可完成的意图列表
    "ui_hierarchy": dict        # 可选，UI结构（用于后续匹配）
}
```

**主要行为**：
1. 生成页面ID（基于app_id和page_name）
2. 创建页面节点并添加到图谱
3. 生成页面的向量表示并存储
4. 如果提供UI结构，提取特征用于后续匹配

**输出格式**：
```python
{
    "success": bool,
    "page_id": str,             # 生成的页面ID
    "message": str              # 成功或失败消息
}
```

---

### 2.3 注册意图 (`register_intent`)

**解决痛点**：从"静态规则"到"持续学习"，支持新意图的注册

**接口说明**：注册新的用户意图，用于后续的路径查询。

**输入参数**：
```python
{
    "app_id": str,              # 必需，应用ID
    "intent_text": str,         # 必需，意图文本，如 "点外卖"、"查找附近餐厅"
    "target_page": str,         # 可选，目标页面ID（如果已知）
    "keywords": [str]           # 可选，关键词列表，如 ["外卖", "点餐", "下单"]
}
```

**主要行为**：
1. 生成意图ID
2. 生成意图的向量表示
3. 存储到向量数据库
4. 如果提供目标页面，建立意图到页面的关联

**输出格式**：
```python
{
    "success": bool,
    "intent_id": str,           # 生成的意图ID
    "message": str
}
```

---

## 三、辅助查询接口

### 3.1 获取页面可用操作 (`get_available_actions`)

**解决痛点**：从"盲目探索"到"智能导航"

**接口说明**：获取指定页面的所有可用操作（出边转换）。

**输入参数**：
```python
{
    "page_id": str              # 必需，页面ID
}
```

**主要行为**：
1. 查找页面的所有出边转换
2. 按成功率排序
3. 返回操作列表

**输出格式**：
```python
{
    "page_id": str,
    "page_name": str,
    "actions": [
        {
            "action_type": str,
            "widget_id": str,
            "widget_text": str,
            "target_page_id": str,
            "target_page_name": str,
            "success_rate": float,
            "avg_latency_ms": float,
            "description": str
        }
    ],
    "total_count": int
}
```

---

### 3.2 查找相似意图 (`find_similar_intents`)

**解决痛点**：从"单App测试"到"跨App知识复用"

**接口说明**：根据查询文本查找相似的已注册意图，支持跨App知识复用。

**输入参数**：
```python
{
    "query": str,               # 必需，查询文本
    "app_id": str,              # 可选，限制在特定App内查找
    "top_k": int                # 可选，返回前K个结果，默认5
}
```

**主要行为**：
1. 使用向量相似度搜索
2. 如果指定app_id，仅在对应App内搜索
3. 返回相似度最高的意图列表

**输出格式**：
```python
{
    "intents": [
        {
            "intent_id": str,
            "intent_text": str,
            "app_id": str,
            "target_page": str,
            "similarity": float,    # 相似度分数
            "keywords": [str]
        }
    ],
    "total_found": int
}
```

---

### 3.3 获取图谱统计信息 (`get_graph_stats`)

**解决痛点**：从"难以调试"到"可解释路径"

**接口说明**：获取图谱的整体统计信息，用于监控和调试。

**输入参数**：
```python
{}                              # 无需参数，或可选的app_id
```

**主要行为**：
1. 统计节点数量（App、Page、Widget等）
2. 统计边数量（转换关系）
3. 统计意图数量
4. 计算平均路径长度、成功率等指标

**输出格式**：
```python
{
    "apps": int,                # App数量
    "pages": int,               # 页面数量
    "transitions": int,          # 转换关系数量
    "intents": int,             # 意图数量
    "avg_path_length": float,   # 平均路径长度
    "avg_success_rate": float,  # 平均成功率
    "last_updated": str         # 最后更新时间
}
```

---

## 四、批量操作接口

### 4.1 批量添加页面转换 (`batch_add_transitions`)

**解决痛点**：提高图谱构建效率

**接口说明**：批量添加页面转换关系，用于初始图谱构建。

**输入参数**：
```python
{
    "transitions": [            # 转换关系列表
        {
            "from_page": str,
            "to_page": str,
            "action_type": str,
            "widget_text": str,
            "success_count": int,   # 可选，初始成功次数
            "fail_count": int       # 可选，初始失败次数
        }
    ]
}
```

**主要行为**：
1. 批量创建转换关系
2. 如果转换已存在，更新统计信息
3. 返回成功和失败的数量

**输出格式**：
```python
{
    "success": bool,
    "total": int,               # 总数
    "created": int,             # 新建数量
    "updated": int,             # 更新数量
    "failed": int,              # 失败数量
    "errors": [str]             # 错误信息列表
}
```

---

## 五、错误处理

所有接口在遇到错误时，应返回统一的错误格式：

```python
{
    "success": False,
    "error": {
        "code": str,            # 错误代码，如 "PAGE_NOT_FOUND", "INVALID_PARAMETER"
        "message": str,         # 错误描述
        "details": dict         # 详细信息（可选）
    }
}
```

**常见错误代码**：
- `INVALID_PARAMETER`: 参数无效
- `PAGE_NOT_FOUND`: 页面不存在
- `INTENT_NOT_FOUND`: 意图未找到
- `PATH_NOT_FOUND`: 无法找到路径
- `GRAPH_ERROR`: 图谱操作错误
- `VECTOR_STORE_ERROR`: 向量存储错误

---

## 六、接口使用示例

### 典型工作流程

```python
from agent_interface import KGClient

# 1. 初始化客户端
kg = KGClient()

# 2. 匹配当前页面（如果不知道当前页面ID）
page_info = kg.match_current_page(
    app_id="com.meituan.app",
    page_title="首页"
)
current_page_id = page_info["page"]["page_id"]

# 3. 查询操作路径
result = kg.query_path(
    app_id="com.meituan.app",
    intent="点外卖",
    current_page=current_page_id
)

# 4. 执行操作
if result["success"]:
    for step in result["path"]["steps"]:
        # 执行操作
        execute_action(
            action_type=step["action_type"],
            widget_text=step["widget_text"]
        )
        
        # 等待页面加载
        new_page = wait_for_page_load()
        
        # 上报结果
        kg.report_transition(
            from_page=step.get("from_page", current_page_id),
            action={
                "type": step["action_type"],
                "widget_text": step["widget_text"]
            },
            to_page=step["expected_page"],
            success=True,
            latency_ms=500
        )
        
        current_page_id = step["expected_page"]
```

---

## 七、接口设计总结

### 输入要求最小化
- 核心接口（如`query_path`）只需提供`app_id`和`intent`即可工作
- 可选参数提供默认值，降低使用门槛
- UI结构信息可选，系统能通过其他方式（如标题）匹配页面

### 输出结构化且信息丰富
- 所有接口返回统一的JSON格式
- 包含置信度、成功率等可解释性信息
- 提供备选方案和错误信息

### 支持持续学习
- `report_transition`接口允许Agent上报执行结果
- 系统自动更新统计信息，无需人工干预
- 支持动态添加新页面和意图

### 兼顾实时性和全局性
- `get_next_action`支持实时决策
- `query_path`支持全局路径规划
- 两种模式可灵活切换

