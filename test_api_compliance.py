#!/usr/bin/env python3
"""
API規範符合性測試

此測試腳本驗證所有接口是否符合 API_SPECIFICATION.md 中定義的規範。
包括：
1. 接口輸入輸出格式
2. 錯誤處理格式
3. 嵌入模型使用
4. 所有必需接口的實現
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_interface.kg_client import KGClient
from kg_core.schema import Page, Transition, PageType, ActionType
from datetime import datetime


def test_embedding_model():
    """測試嵌入模型是否正確加載"""
    print("=" * 60)
    print("測試1: 嵌入模型加載")
    print("=" * 60)
    
    from kg_core.embeddings import EmbeddingModel
    
    try:
        embedder = EmbeddingModel(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_folder="./embedding_models"
        )
        
        # 測試編碼
        test_text = "點外賣"
        vec = embedder.encode_single(test_text)
        
        print(f"✓ 模型加載成功")
        print(f"  向量維度: {len(vec)}")
        print(f"  測試文本: '{test_text}'")
        print(f"  向量前5維: {vec[:5]}")
        
        return embedder
    except Exception as e:
        print(f"✗ 模型加載失敗: {e}")
        return None


def setup_test_graph(kg_client: KGClient):
    """設置測試用的知識圖譜"""
    print("\n" + "=" * 60)
    print("測試2: 構建測試圖譜")
    print("=" * 60)
    
    app_id = "com.test.app"
    
    # 添加頁面
    pages = [
        ("首頁", "首頁，包含主要入口", ["打開外賣", "打開美食"]),
        ("外賣首頁", "外賣頻道首頁", ["搜索外賣", "查看商家"]),
        ("商家列表", "商家列表頁", ["選擇商家"]),
        ("商家詳情", "商家詳情頁", ["加入購物車", "查看評價"]),
        ("購物車", "購物車頁面", ["去結算"]),
        ("訂單確認", "訂單確認頁", ["提交訂單"]),
    ]
    
    page_ids = {}
    for name, desc, intents in pages:
        page_id = kg_client.add_page(
            app_id=app_id,
            page_name=name,
            page_type="home" if name == "首頁" else "other",
            description=desc,
            intents=intents
        )
        page_ids[name] = page_id
        print(f"  ✓ 添加頁面: {name} ({page_id[:8]}...)")
    
    # 批量添加轉換關係
    transitions = [
        {"from_page": page_ids["首頁"], "to_page": page_ids["外賣首頁"], 
         "action_type": "click", "widget_text": "外賣", "success_count": 10},
        {"from_page": page_ids["外賣首頁"], "to_page": page_ids["商家列表"], 
         "action_type": "click", "widget_text": "查看更多", "success_count": 10},
        {"from_page": page_ids["商家列表"], "to_page": page_ids["商家詳情"], 
         "action_type": "click", "widget_text": "商家卡片", "success_count": 10},
        {"from_page": page_ids["商家詳情"], "to_page": page_ids["購物車"], 
         "action_type": "click", "widget_text": "購物車", "success_count": 10},
        {"from_page": page_ids["購物車"], "to_page": page_ids["訂單確認"], 
         "action_type": "click", "widget_text": "去結算", "success_count": 10},
    ]
    
    result = kg_client.batch_add_transitions(transitions)
    print(f"\n  ✓ 批量添加轉換: 創建 {result['created']}, 更新 {result['updated']}")
    
    # 註冊意圖
    intents = [
        ("點外賣", page_ids["訂單確認"], ["外賣", "點餐"]),
        ("查看商家", page_ids["商家列表"], ["商家", "餐廳"]),
    ]
    
    for text, target, keywords in intents:
        intent_id = kg_client.register_intent(
            app_id=app_id,
            intent_text=text,
            target_page=target,
            keywords=keywords
        )
        print(f"  ✓ 註冊意圖: {text} ({intent_id[:8]}...)")
    
    return app_id, page_ids


def test_query_path(kg_client: KGClient, app_id: str, page_ids: dict):
    """測試 query_path 接口"""
    print("\n" + "=" * 60)
    print("測試3: query_path 接口")
    print("=" * 60)
    
    result = kg_client.query_path(
        app_id=app_id,
        intent="點外賣",
        current_page=page_ids["首頁"],
        max_steps=10
    )
    
    # 檢查輸出格式
    required_fields = ["success", "message", "confidence"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in result:
            print(f"  ✓ {field}: {result[field]}")
        else:
            print(f"  ✗ 缺少字段: {field}")
    
    if result.get("success"):
        path = result.get("path", {})
        path_fields = ["total_steps", "estimated_time_ms", "steps"]
        print("\n檢查 path 字段:")
        for field in path_fields:
            if field in path:
                print(f"  ✓ path.{field}: {path[field]}")
            else:
                print(f"  ✗ 缺少字段: path.{field}")
        
        if "steps" in path and path["steps"]:
            step = path["steps"][0]
            step_fields = ["step", "action_type", "widget_id", "widget_text", 
                          "expected_page", "confidence", "description"]
            print("\n檢查 step 字段:")
            for field in step_fields:
                if field in step:
                    print(f"  ✓ step.{field}: {step[field]}")
                else:
                    print(f"  ✗ 缺少字段: step.{field}")
        
        if "target_page" in result:
            print(f"  ✓ target_page: {result['target_page']}")
        else:
            print(f"  ⚠ target_page 字段缺失（可選）")
    
    return result


def test_get_next_action(kg_client: KGClient, page_ids: dict):
    """測試 get_next_action 接口"""
    print("\n" + "=" * 60)
    print("測試4: get_next_action 接口")
    print("=" * 60)
    
    action = kg_client.get_next_action(
        current_page=page_ids["首頁"],
        intent="點外賣",
        app_id="com.test.app"
    )
    
    if action:
        action_dict = action.to_dict()
        required_fields = ["action", "is_complete", "remaining_steps"]
        print("\n檢查必需字段:")
        for field in required_fields:
            if field in action_dict:
                print(f"  ✓ {field}: {action_dict[field]}")
            else:
                print(f"  ✗ 缺少字段: {field}")
    else:
        print("  ⚠ 返回 None（可能已到達目標）")


def test_match_current_page(kg_client: KGClient, app_id: str):
    """測試 match_current_page 接口"""
    print("\n" + "=" * 60)
    print("測試5: match_current_page 接口")
    print("=" * 60)
    
    result = kg_client.match_current_page(
        app_id=app_id,
        page_title="首頁"
    )
    
    required_fields = ["matched", "page", "available_actions", "candidates"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in result:
            print(f"  ✓ {field}: {type(result[field]).__name__}")
        else:
            print(f"  ✗ 缺少字段: {field}")
    
    if result.get("matched") and result.get("page"):
        page = result["page"]
        page_fields = ["page_id", "page_name", "confidence"]
        print("\n檢查 page 字段:")
        for field in page_fields:
            if field in page:
                print(f"  ✓ page.{field}: {page[field]}")
            else:
                print(f"  ✗ 缺少字段: page.{field}")


def test_get_rag_context(kg_client: KGClient, app_id: str, page_ids: dict):
    """測試 get_rag_context 接口"""
    print("\n" + "=" * 60)
    print("測試6: get_rag_context 接口")
    print("=" * 60)
    
    context = kg_client.get_rag_context(
        app_id=app_id,
        query="我想點外賣",
        current_page=page_ids["首頁"]
    )
    
    required_fields = ["prompt", "context", "suggested_actions"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in context:
            print(f"  ✓ {field}: {type(context[field]).__name__}")
        else:
            print(f"  ✗ 缺少字段: {field}")
    
    if "context" in context:
        ctx = context["context"]
        ctx_fields = ["relevant_pages", "recommended_paths", "historical_cases", "tips"]
        print("\n檢查 context 字段:")
        for field in ctx_fields:
            if field in ctx:
                print(f"  ✓ context.{field}: {type(ctx[field]).__name__}")
            else:
                print(f"  ✗ 缺少字段: context.{field}")


def test_get_available_actions(kg_client: KGClient, page_ids: dict):
    """測試 get_available_actions 接口"""
    print("\n" + "=" * 60)
    print("測試7: get_available_actions 接口")
    print("=" * 60)
    
    result = kg_client.get_available_actions(page_ids["首頁"])
    
    required_fields = ["page_id", "page_name", "actions", "total_count"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in result:
            print(f"  ✓ {field}: {result[field]}")
        else:
            print(f"  ✗ 缺少字段: {field}")


def test_find_similar_intents(kg_client: KGClient, app_id: str):
    """測試 find_similar_intents 接口"""
    print("\n" + "=" * 60)
    print("測試8: find_similar_intents 接口")
    print("=" * 60)
    
    result = kg_client.find_similar_intents(
        query="我想點餐",
        app_id=app_id,
        top_k=5
    )
    
    required_fields = ["intents", "total_found"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in result:
            print(f"  ✓ {field}: {result[field]}")
        else:
            print(f"  ✗ 缺少字段: {field}")
    
    if result.get("intents"):
        intent = result["intents"][0]
        intent_fields = ["intent_id", "intent_text", "app_id", "similarity"]
        print("\n檢查 intent 字段:")
        for field in intent_fields:
            if field in intent:
                print(f"  ✓ intent.{field}: {intent[field]}")
            else:
                print(f"  ✗ 缺少字段: intent.{field}")


def test_get_graph_stats(kg_client: KGClient):
    """測試 get_graph_stats 接口"""
    print("\n" + "=" * 60)
    print("測試9: get_graph_stats 接口")
    print("=" * 60)
    
    stats = kg_client.get_graph_stats()
    
    required_fields = ["apps", "pages", "transitions", "intents", 
                      "avg_path_length", "avg_success_rate", "last_updated"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in stats:
            print(f"  ✓ {field}: {stats[field]}")
        else:
            print(f"  ✗ 缺少字段: {field}")


def test_report_transition(kg_client: KGClient, page_ids: dict):
    """測試 report_transition 接口"""
    print("\n" + "=" * 60)
    print("測試10: report_transition 接口")
    print("=" * 60)
    
    result = kg_client.report_transition(
        from_page=page_ids["首頁"],
        action={"type": "click", "widget_text": "測試按鈕"},
        to_page=page_ids["外賣首頁"],
        success=True,
        latency_ms=200
    )
    
    required_fields = ["success", "transition_id", "updated", "stats"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in result:
            print(f"  ✓ {field}: {result[field]}")
        else:
            print(f"  ✗ 缺少字段: {field}")
    
    if "stats" in result:
        stats = result["stats"]
        stats_fields = ["success_count", "fail_count", "success_rate", "avg_latency_ms"]
        print("\n檢查 stats 字段:")
        for field in stats_fields:
            if field in stats:
                print(f"  ✓ stats.{field}: {stats[field]}")
            else:
                print(f"  ✗ 缺少字段: stats.{field}")


def test_batch_add_transitions(kg_client: KGClient, page_ids: dict):
    """測試 batch_add_transitions 接口"""
    print("\n" + "=" * 60)
    print("測試11: batch_add_transitions 接口")
    print("=" * 60)
    
    transitions = [
        {
            "from_page": page_ids["外賣首頁"],
            "to_page": page_ids["商家列表"],
            "action_type": "click",
            "widget_text": "測試按鈕",
            "success_count": 5
        }
    ]
    
    result = kg_client.batch_add_transitions(transitions)
    
    required_fields = ["success", "total", "created", "updated", "failed", "errors"]
    print("\n檢查必需字段:")
    for field in required_fields:
        if field in result:
            print(f"  ✓ {field}: {result[field]}")
        else:
            print(f"  ✗ 缺少字段: {field}")


def main():
    """主測試函數"""
    print("\n" + "=" * 60)
    print("API規範符合性測試")
    print("=" * 60)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 測試嵌入模型
    embedder = test_embedding_model()
    if not embedder:
        print("\n❌ 嵌入模型測試失敗，無法繼續")
        return
    
    # 初始化KG客戶端
    kg_client = KGClient(embedding_model=embedder)
    
    # 構建測試圖譜
    app_id, page_ids = setup_test_graph(kg_client)
    
    # 執行所有接口測試
    test_query_path(kg_client, app_id, page_ids)
    test_get_next_action(kg_client, page_ids)
    test_match_current_page(kg_client, app_id)
    test_get_rag_context(kg_client, app_id, page_ids)
    test_get_available_actions(kg_client, page_ids)
    test_find_similar_intents(kg_client, app_id)
    test_get_graph_stats(kg_client)
    test_report_transition(kg_client, page_ids)
    test_batch_add_transitions(kg_client, page_ids)
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
    print(f"結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    main()

