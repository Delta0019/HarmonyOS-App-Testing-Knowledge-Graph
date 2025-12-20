#!/usr/bin/env python3
"""
示例: 构建美团App的知识图谱

这个示例展示如何:
1. 初始化知识图谱
2. 添加页面节点
3. 添加页面转换关系
4. 注册用户意图
5. 查询路径
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kg_core.schema import App, Page, Widget, Transition, PageType, WidgetType, ActionType
from kg_core.graph_store import MemoryGraphStore
from kg_core.vector_store import VectorStoreManager
from kg_core.embeddings import EmbeddingModel
from agent_interface.kg_client import KGClient


def build_meituan_graph():
    """
    构建美团App的示例图谱
    
    页面结构:
    首页 ─┬─> 外卖首页 ─┬─> 商家列表 ─> 商家详情 ─> 购物车 ─> 订单确认
          │             └─> 搜索页 ─> 搜索结果
          ├─> 美食频道 ─> 餐厅列表 ─> 餐厅详情
          ├─> 酒店频道 ─> 酒店列表 ─> 酒店详情
          └─> 我的 ─┬─> 我的订单
                   └─> 我的优惠券
    """
    
    print("=" * 60)
    print("构建美团App知识图谱")
    print("=" * 60)
    
    # 1. 初始化组件
    print("\n[1] 初始化图谱组件...")
    graph = MemoryGraphStore()
    vectors = VectorStoreManager(mode="memory", dimension=384)
    embedder = EmbeddingModel(use_mock=True)  # Demo使用Mock模型
    
    # 2. 创建应用
    print("[2] 创建应用节点...")
    app = App(
        app_id="com.meituan.app",
        app_name="美团",
        version="12.5.0",
        platform="harmonyos"
    )
    graph.add_app(app)
    
    # 3. 定义页面
    print("[3] 添加页面节点...")
    
    pages_data = [
        # (名称, 类型, 描述, 可完成的意图)
        ("首页", PageType.HOME, "美团App首页，包含外卖、美食、酒店等入口", 
         ["打开外卖", "打开美食", "打开酒店", "查看我的"]),
        
        ("外卖首页", PageType.LIST, "外卖频道首页，显示附近商家和推荐",
         ["搜索外卖", "查看商家列表", "筛选商家"]),
        
        ("商家列表", PageType.LIST, "外卖商家列表页，可筛选和排序",
         ["选择商家", "筛选距离", "筛选评分"]),
        
        ("商家详情", PageType.DETAIL, "商家详情页，显示菜单和评价",
         ["查看菜单", "加入购物车", "查看评价"]),
        
        ("购物车", PageType.FORM, "购物车页面，显示已选商品",
         ["修改数量", "删除商品", "去结算"]),
        
        ("订单确认", PageType.FORM, "订单确认页，填写地址和支付",
         ["修改地址", "使用优惠券", "提交订单"]),
        
        ("搜索页", PageType.SEARCH, "搜索页面，可输入关键词搜索",
         ["搜索商家", "搜索菜品"]),
        
        ("搜索结果", PageType.LIST, "搜索结果页，显示匹配的商家",
         ["查看搜索结果", "选择商家"]),
        
        ("美食频道", PageType.LIST, "美食频道首页，显示附近餐厅",
         ["查找餐厅", "筛选菜系"]),
        
        ("餐厅列表", PageType.LIST, "餐厅列表页",
         ["选择餐厅", "查看排行"]),
        
        ("餐厅详情", PageType.DETAIL, "餐厅详情页，显示信息和评价",
         ["查看餐厅详情", "预约餐厅", "导航到店"]),
        
        ("我的", PageType.OTHER, "个人中心页面",
         ["查看订单", "查看优惠券", "修改设置"]),
        
        ("我的订单", PageType.LIST, "订单列表页",
         ["查看订单详情", "再来一单"]),
        
        ("我的优惠券", PageType.LIST, "优惠券列表页",
         ["查看优惠券", "使用优惠券"]),
    ]
    
    page_ids = {}
    for name, ptype, desc, intents in pages_data:
        page_id = Page.generate_id(app.app_id, name)
        page = Page(
            page_id=page_id,
            page_name=name,
            app_id=app.app_id,
            page_type=ptype,
            description=desc,
            intents=intents,
            keywords=name.split()
        )
        graph.add_page(page)
        page_ids[name] = page_id
        
        # 添加向量
        vec = embedder.encode_single(f"{name} {desc}")
        vectors.pages.insert(page_id, vec, {
            "name": name,
            "description": desc,
            "intents": intents
        })
    
    print(f"   添加了 {len(page_ids)} 个页面")
    
    # 4. 定义转换关系
    print("[4] 添加页面转换关系...")
    
    transitions_data = [
        # (源页面, 目标页面, 触发控件文本, 操作类型)
        ("首页", "外卖首页", "外卖", ActionType.CLICK),
        ("首页", "美食频道", "美食", ActionType.CLICK),
        ("首页", "我的", "我的", ActionType.CLICK),
        
        ("外卖首页", "商家列表", "查看更多", ActionType.CLICK),
        ("外卖首页", "搜索页", "搜索框", ActionType.CLICK),
        ("外卖首页", "商家详情", "商家卡片", ActionType.CLICK),
        
        ("搜索页", "搜索结果", "搜索按钮", ActionType.CLICK),
        ("搜索结果", "商家详情", "商家卡片", ActionType.CLICK),
        
        ("商家列表", "商家详情", "商家卡片", ActionType.CLICK),
        ("商家详情", "购物车", "购物车按钮", ActionType.CLICK),
        ("商家详情", "商家详情", "加入购物车", ActionType.CLICK),  # 自循环
        
        ("购物车", "订单确认", "去结算", ActionType.CLICK),
        ("购物车", "商家详情", "继续选购", ActionType.CLICK),
        
        ("订单确认", "我的订单", "提交订单", ActionType.CLICK),
        
        ("美食频道", "餐厅列表", "附近美食", ActionType.CLICK),
        ("餐厅列表", "餐厅详情", "餐厅卡片", ActionType.CLICK),
        
        ("我的", "我的订单", "我的订单", ActionType.CLICK),
        ("我的", "我的优惠券", "优惠券", ActionType.CLICK),
        
        # 返回关系
        ("外卖首页", "首页", "返回", ActionType.BACK),
        ("商家详情", "商家列表", "返回", ActionType.BACK),
        ("购物车", "商家详情", "返回", ActionType.BACK),
    ]
    
    for src, tgt, widget_text, action in transitions_data:
        if src in page_ids and tgt in page_ids:
            trans = Transition(
                transition_id=Transition.generate_id(page_ids[src], page_ids[tgt], action.value),
                source_page_id=page_ids[src],
                target_page_id=page_ids[tgt],
                trigger_widget_text=widget_text,
                action_type=action,
                success_count=10  # 初始成功次数
            )
            graph.add_transition(trans)
    
    print(f"   添加了 {len(transitions_data)} 个转换关系")
    
    # 5. 注册意图
    print("[5] 注册用户意图...")
    
    intents_data = [
        ("点外卖", "订单确认", ["外卖", "点餐", "下单"]),
        ("查找附近餐厅", "餐厅列表", ["餐厅", "美食", "附近"]),
        ("搜索商家", "搜索结果", ["搜索", "查找"]),
        ("查看订单", "我的订单", ["订单", "历史"]),
        ("使用优惠券", "我的优惠券", ["优惠券", "折扣"]),
    ]
    
    from kg_core.schema import Intent
    for text, target, keywords in intents_data:
        intent_id = Intent.generate_id(app.app_id, text)
        vec = embedder.encode_single(text)
        vectors.intents.insert(intent_id, vec, {
            "text": text,
            "target_page_id": page_ids.get(target, ""),
            "keywords": keywords
        })
    
    print(f"   注册了 {len(intents_data)} 个意图")
    
    # 6. 打印统计
    print("\n[6] 图谱统计:")
    stats = graph.get_graph_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return graph, vectors, embedder, page_ids


def demo_query(graph, vectors, embedder, page_ids):
    """演示查询功能"""
    
    print("\n" + "=" * 60)
    print("演示：路径查询")
    print("=" * 60)
    
    # 创建客户端
    kg = KGClient(
        graph_store=graph,
        vector_store=vectors,
        embedding_model=embedder
    )
    
    # 查询1: 点外卖
    print("\n[查询1] 意图: '点外卖'")
    print("-" * 40)
    result = kg.query_path(
        app_id="com.meituan.app",
        intent="点外卖",
        current_page=page_ids["首页"]
    )
    
    if result["success"]:
        print(f"✓ 找到路径，共 {result['path']['total_steps']} 步")
        print(f"  置信度: {result['confidence']:.2f}")
        print("  步骤:")
        for step in result["path"]["steps"]:
            print(f"    {step['step']}. {step['description']}")
    else:
        print(f"✗ {result['message']}")
    
    # 查询2: 查找餐厅
    print("\n[查询2] 意图: '查找附近餐厅'")
    print("-" * 40)
    result = kg.query_path(
        app_id="com.meituan.app",
        intent="查找附近餐厅",
        current_page=page_ids["首页"]
    )
    
    if result["success"]:
        print(f"✓ 找到路径，共 {result['path']['total_steps']} 步")
        for step in result["path"]["steps"]:
            print(f"    {step['step']}. {step['description']}")
    
    # 查询3: 获取下一步操作
    print("\n[查询3] 获取下一步操作")
    print("-" * 40)
    action = kg.get_next_action(
        current_page=page_ids["外卖首页"],
        intent="点外卖"
    )
    if action:
        print(f"✓ 推荐操作: {action.action_type}")
        print(f"  控件: {action.widget_text}")
        print(f"  预期页面: {action.expected_page}")
    
    # 查询4: 获取RAG上下文
    print("\n[查询4] 获取RAG上下文")
    print("-" * 40)
    context = kg.get_rag_context(
        app_id="com.meituan.app",
        query="我想点一份外卖",
        current_page=page_ids["首页"]
    )
    print("生成的提示词:")
    print(context["prompt"][:500] + "..." if len(context["prompt"]) > 500 else context["prompt"])


def main():
    """主函数"""
    # 构建图谱
    graph, vectors, embedder, page_ids = build_meituan_graph()
    
    # 演示查询
    demo_query(graph, vectors, embedder, page_ids)
    
    print("\n" + "=" * 60)
    print("Demo完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
