# HarmonyOS App Testing Knowledge Graph

鸿蒙系统App自动化测试知识图谱系统

## 📁 项目结构

```
harmonyos_kg/
├── config/
│   └── config.yaml          # 配置文件
├── kg_core/                  # 核心模块
│   ├── schema.py            # Schema定义（实体+关系）
│   ├── graph_store.py       # 图数据库操作
│   ├── vector_store.py      # 向量数据库操作
│   └── embeddings.py        # 嵌入模型封装
├── kg_builder/              # 图谱构建模块
│   ├── page_extractor.py    # 页面信息提取
│   ├── intent_generator.py  # 意图生成（LLM）
│   └── graph_builder.py     # 图谱构建器
├── kg_query/                # 查询模块
│   ├── path_finder.py       # 路径查询
│   ├── page_matcher.py      # 页面匹配
│   └── rag_engine.py        # RAG引擎
├── api/                     # API服务
│   ├── routes.py            # REST接口
│   └── models.py            # 数据模型
├── agent_interface/         # Agent对接层
│   └── kg_client.py         # GUI Agent客户端
└── examples/                # 示例代码
    ├── demo_build_graph.py  # 构建图谱示例
    ├── demo_query.py        # 查询示例
    └── demo_with_agent.py   # Agent对接示例
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

```bash
# 启动Neo4j (使用Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5.12.0

# 或使用内存模式运行Demo（无需数据库）
python examples/demo_build_graph.py --in-memory
```

### 3. 运行示例

```bash
# 构建图谱
python examples/demo_build_graph.py

# 查询路径
python examples/demo_query.py

# Agent对接示例
python examples/demo_with_agent.py
```

## 🔌 与GUI Agent对接

### 方式1: 直接调用SDK

```python
from agent_interface.kg_client import KGClient

# 初始化客户端
kg = KGClient()

# Agent决策时查询路径
path = kg.query_path(
    app_id="com.meituan.app",
    intent="查找附近餐厅",
    current_page="home"
)

# 执行操作后更新图谱
kg.report_transition(
    from_page="home",
    action={"type": "click", "widget": "search_btn"},
    to_page="search_page"
)
```

### 方式2: REST API

```bash
# 启动API服务
python -m api.routes

# 查询路径
curl -X POST http://localhost:8000/api/v1/query/path \
  -H "Content-Type: application/json" \
  -d '{"app_id": "com.meituan.app", "intent": "查找附近餐厅"}'
```

## 📊 核心数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  GUI Agent  │────▶│  KG Client  │────▶│  KG Service │
│  (测试执行)  │◀────│  (对接层)    │◀────│  (查询/更新) │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
             ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
             │  Graph DB   │          │ Vector DB   │          │    Cache    │
             │  (Neo4j)    │          │  (Milvus)   │          │   (Redis)   │
             └─────────────┘          └─────────────┘          └─────────────┘
```
