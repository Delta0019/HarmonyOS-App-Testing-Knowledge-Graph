"""
知识图谱客户端 - GUI Agent对接层

这是GUI Agent与知识图谱系统交互的主要接口

使用方式:
    from agent_interface import KGClient
    
    kg = KGClient()
    
    # 查询操作路径
    result = kg.query_path("com.meituan.app", "查找附近餐厅")
    
    # 获取下一步操作
    action = kg.get_next_action("home_page", "查找附近餐厅")
    
    # 上报操作结果
    kg.report_action_result(action_id, success=True)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kg_core.schema import Page, Widget, Transition, ActionType, PageType
from kg_core.graph_store import MemoryGraphStore
from kg_core.vector_store import VectorStoreManager
from kg_core.embeddings import EmbeddingModel
from kg_query.path_finder import PathFinder
from kg_query.page_matcher import PageMatcher
from kg_query.rag_engine import RAGEngine


@dataclass
class ActionRecommendation:
    """操作推荐"""
    action_type: str          # click, input, swipe, etc.
    widget_id: str
    widget_text: str
    input_text: str = ""      # 输入类型时的文本
    confidence: float = 0.0
    expected_page: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action_type,
            "widget_id": self.widget_id,
            "widget_text": self.widget_text,
            "input_text": self.input_text,
            "confidence": self.confidence,
            "expected_page": self.expected_page,
            "description": self.description
        }


class KGClient:
    """
    知识图谱客户端
    
    为GUI Agent提供的统一接口，封装了图谱的查询和更新操作
    
    核心方法:
    - query_path(): 根据意图查询操作路径
    - get_next_action(): 获取下一步推荐操作
    - match_current_page(): 匹配当前页面
    - report_transition(): 上报页面转换（用于图谱学习）
    """
    
    def __init__(
        self,
        graph_store: MemoryGraphStore = None,
        vector_store: VectorStoreManager = None,
        embedding_model: EmbeddingModel = None,
        api_endpoint: str = None
    ):
        """
        初始化客户端
        
        Args:
            graph_store: 图存储实例（本地模式）
            vector_store: 向量存储实例（本地模式）
            embedding_model: 嵌入模型（本地模式）
            api_endpoint: API端点（远程模式）
        """
        self.api_endpoint = api_endpoint
        
        # 本地模式
        if api_endpoint is None:
            self.graph = graph_store or MemoryGraphStore()
            self.vectors = vector_store or VectorStoreManager(mode="memory")
            self.embedder = embedding_model or EmbeddingModel(use_mock=True)
            
            # 初始化查询引擎
            self.path_finder = PathFinder(self.graph, self.vectors, self.embedder)
            self.page_matcher = PageMatcher(self.graph, self.vectors, self.embedder)
            self.rag_engine = RAGEngine(self.graph, self.vectors, self.embedder)
            
            self._is_local = True
        else:
            self._is_local = False
            self._init_http_client()
    
    def _init_http_client(self):
        """初始化HTTP客户端"""
        try:
            import httpx
            self._http = httpx.Client(base_url=self.api_endpoint, timeout=30.0)
        except ImportError:
            raise ImportError("远程模式需要安装httpx: pip install httpx")
    
    # ==================== 核心查询接口 ====================
    
    def query_path(
        self,
        app_id: str,
        intent: str,
        current_page: str = None,
        max_steps: int = 10
    ) -> Dict:
        """
        根据意图查询操作路径
        
        这是GUI Agent最常用的接口
        
        Args:
            app_id: 应用ID，如 "com.meituan.app"
            intent: 用户意图，如 "查找附近的川菜餐厅"
            current_page: 当前页面ID（可选）
            max_steps: 最大步骤数
            
        Returns:
            {
                "success": True,
                "path": {
                    "steps": [...],
                    "total_steps": 3,
                    "confidence": 0.92
                },
                "alternatives": [...],
                "message": "找到路径"
            }
        
        Example:
            >>> kg = KGClient()
            >>> result = kg.query_path("com.meituan.app", "点外卖")
            >>> if result["success"]:
            ...     for step in result["path"]["steps"]:
            ...         print(f"步骤{step['step']}: {step['description']}")
        """
        if self._is_local:
            result = self.path_finder.find_path_by_intent(
                app_id=app_id,
                intent=intent,
                current_page_id=current_page,
                max_steps=max_steps
            )
            return result.to_dict()
        else:
            response = self._http.post("/api/v1/query/path", json={
                "app_id": app_id,
                "intent": intent,
                "current_page_id": current_page,
                "max_steps": max_steps
            })
            return response.json()
    
    def get_next_action(
        self,
        current_page: str,
        intent: str,
        app_id: str = ""
    ) -> Optional[ActionRecommendation]:
        """
        获取下一步推荐操作
        
        用于Agent的实时决策，只返回立即需要执行的操作
        
        Args:
            current_page: 当前页面ID
            intent: 目标意图
            app_id: 应用ID
            
        Returns:
            ActionRecommendation 或 None
            
        Example:
            >>> action = kg.get_next_action("home_page", "搜索餐厅")
            >>> if action:
            ...     print(f"执行: {action.action_type} on {action.widget_text}")
        """
        if self._is_local:
            next_action = self.path_finder.get_next_action(current_page, intent)
            if next_action:
                return ActionRecommendation(
                    action_type=next_action["action"],
                    widget_id=next_action["widget_id"],
                    widget_text=next_action.get("widget_text", ""),
                    confidence=next_action.get("confidence", 0.0),
                    expected_page=next_action.get("expected_page", ""),
                    description=next_action.get("description", "")
                )
            return None
        else:
            response = self._http.post("/api/v1/query/next-action", json={
                "current_page_id": current_page,
                "intent": intent,
                "app_id": app_id
            })
            data = response.json()
            if data.get("action"):
                return ActionRecommendation(**data["action"])
            return None
    
    def match_current_page(
        self,
        app_id: str,
        ui_hierarchy: Dict = None,
        page_title: str = None
    ) -> Optional[Dict]:
        """
        匹配当前页面
        
        根据UI结构或标题匹配图谱中的页面
        
        Args:
            app_id: 应用ID
            ui_hierarchy: UI控件树
            page_title: 页面标题
            
        Returns:
            {
                "page_id": "xxx",
                "page_name": "首页",
                "confidence": 0.95,
                "available_actions": [...]
            }
        """
        if self._is_local:
            result = self.page_matcher.match_page(
                app_id=app_id,
                ui_hierarchy=ui_hierarchy,
                page_title=page_title
            )
            return result.to_dict() if result else None
        else:
            response = self._http.post("/api/v1/query/match-page", json={
                "app_id": app_id,
                "ui_hierarchy": ui_hierarchy,
                "page_title": page_title
            })
            return response.json()
    
    def get_available_actions(self, page_id: str) -> List[Dict]:
        """
        获取页面的所有可用操作
        
        Args:
            page_id: 页面ID
            
        Returns:
            操作列表，每个包含 widget_id, action_type, leads_to 等
        """
        if self._is_local:
            transitions = self.graph.get_outgoing_transitions(page_id)
            return [t.to_dict() for t in transitions]
        else:
            response = self._http.get(f"/api/v1/pages/{page_id}/actions")
            return response.json()
    
    def get_rag_context(
        self,
        app_id: str,
        query: str,
        current_page: str = None
    ) -> Dict:
        """
        获取RAG上下文
        
        用于需要LLM决策的复杂场景
        
        Returns:
            包含检索结果和提示词的上下文
        """
        if self._is_local:
            context = self.rag_engine.retrieve(
                app_id=app_id,
                query=query,
                current_page_id=current_page
            )
            return context.to_dict()
        else:
            response = self._http.post("/api/v1/rag/retrieve", json={
                "app_id": app_id,
                "query": query,
                "current_page_id": current_page
            })
            return response.json()
    
    # ==================== 图谱更新接口 ====================
    
    def report_transition(
        self,
        from_page: str,
        action: Dict,
        to_page: str,
        success: bool = True,
        latency_ms: int = 0
    ):
        """
        上报页面转换
        
        Agent执行操作后调用，用于图谱学习
        
        Args:
            from_page: 源页面ID
            action: 执行的操作 {"type": "click", "widget": "xxx"}
            to_page: 目标页面ID
            success: 是否成功
            latency_ms: 耗时
            
        Example:
            >>> kg.report_transition(
            ...     from_page="home",
            ...     action={"type": "click", "widget": "search_btn"},
            ...     to_page="search_page",
            ...     success=True
            ... )
        """
        if self._is_local:
            # 查找或创建转换
            transition = self.graph.get_transition(from_page, to_page)
            
            if transition:
                # 更新统计
                self.graph.update_transition_stats(
                    transition.transition_id,
                    success=success,
                    latency_ms=latency_ms
                )
            else:
                # 创建新转换
                trans = Transition(
                    transition_id=Transition.generate_id(
                        from_page, to_page, action.get("type", "click")
                    ),
                    source_page_id=from_page,
                    target_page_id=to_page,
                    trigger_widget_id=action.get("widget", ""),
                    trigger_widget_text=action.get("widget_text", ""),
                    action_type=ActionType(action.get("type", "click")),
                    success_count=1 if success else 0,
                    fail_count=0 if success else 1
                )
                self.graph.add_transition(trans)
        else:
            self._http.post("/api/v1/graph/report-transition", json={
                "from_page": from_page,
                "action": action,
                "to_page": to_page,
                "success": success,
                "latency_ms": latency_ms
            })
    
    def add_page(
        self,
        app_id: str,
        page_name: str,
        page_type: str = "other",
        description: str = "",
        intents: List[str] = None,
        ui_hierarchy: Dict = None
    ) -> str:
        """
        添加新页面到图谱
        
        Returns:
            页面ID
        """
        page_id = Page.generate_id(app_id, page_name)
        
        page = Page(
            page_id=page_id,
            page_name=page_name,
            app_id=app_id,
            page_type=PageType(page_type),
            description=description,
            intents=intents or []
        )
        
        if self._is_local:
            self.graph.add_page(page)
            
            # 生成并存储向量
            if description:
                vec = self.embedder.encode_single(description)
                self.vectors.pages.insert(page_id, vec, {
                    "name": page_name,
                    "description": description,
                    "intents": intents or []
                })
        
        return page_id
    
    def register_intent(
        self,
        app_id: str,
        intent_text: str,
        target_page: str = None,
        keywords: List[str] = None
    ) -> str:
        """
        注册新意图
        
        Returns:
            意图ID
        """
        from kg_core.schema import Intent
        
        intent_id = Intent.generate_id(app_id, intent_text)
        
        if self._is_local:
            # 生成向量
            vec = self.embedder.encode_single(intent_text)
            
            # 存储到向量库
            self.vectors.intents.insert(intent_id, vec, {
                "text": intent_text,
                "app_id": app_id,
                "target_page_id": target_page,
                "keywords": keywords or []
            })
        
        return intent_id
    
    # ==================== 工具方法 ====================
    
    def get_graph_stats(self) -> Dict:
        """获取图谱统计信息"""
        if self._is_local:
            return self.graph.get_graph_stats()
        else:
            response = self._http.get("/api/v1/graph/stats")
            return response.json()
    
    def export_graph(self) -> Dict:
        """导出图谱数据"""
        if self._is_local:
            return self.graph.export_to_dict()
        else:
            response = self._http.get("/api/v1/graph/export")
            return response.json()
    
    def clear_graph(self):
        """清空图谱（谨慎使用）"""
        if self._is_local:
            self.graph.clear()
            self.vectors.pages.clear()
            self.vectors.intents.clear()


# ==================== 便捷函数 ====================

def create_client(
    mode: str = "local",
    api_endpoint: str = None
) -> KGClient:
    """
    创建客户端实例
    
    Args:
        mode: "local" 或 "remote"
        api_endpoint: 远程API地址
    """
    if mode == "remote":
        return KGClient(api_endpoint=api_endpoint)
    return KGClient()
