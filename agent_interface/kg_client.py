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
    is_complete: bool = False  # 是否已到达目标页面
    remaining_steps: int = 0   # 剩余步骤数
    
    def to_dict(self) -> Dict:
        """转换为符合API规范的字典格式"""
        action_dict = {
            "action_type": self.action_type,
            "widget_id": self.widget_id,
            "widget_text": self.widget_text,
            "widget_xpath": getattr(self, 'widget_xpath', ''),
            "input_text": self.input_text,
            "confidence": self.confidence,
            "expected_page": self.expected_page,
            "description": self.description
        }
        
        # 如果已完成，返回None作为action
        if self.is_complete:
            return {
                "action": None,
                "is_complete": True,
                "remaining_steps": 0
            }
        
        return {
            "action": action_dict,
            "is_complete": self.is_complete,
            "remaining_steps": self.remaining_steps
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
            # 使用用户指定的模型，默认使用 all-MiniLM-L6-v2
            self.embedder = embedding_model or EmbeddingModel(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                cache_folder="./embedding_models",
                use_mock=False
            )
            
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
                # 检查是否已完成（remaining_steps == 0）
                remaining_steps = next_action.get("remaining_steps", 0)
                is_complete = remaining_steps == 0
                
                action_rec = ActionRecommendation(
                    action_type=next_action.get("action_type", next_action.get("action", "click")),
                    widget_id=next_action.get("widget_id", ""),
                    widget_text=next_action.get("widget_text", ""),
                    confidence=next_action.get("confidence", 0.0),
                    expected_page=next_action.get("expected_page", ""),
                    description=next_action.get("description", "")
                )
                # 添加额外字段以符合API规范
                action_rec.is_complete = is_complete
                action_rec.remaining_steps = remaining_steps
                return action_rec
            # 如果没有下一步操作，返回已完成状态
            return ActionRecommendation(
                action_type="",
                widget_id="",
                widget_text="",
                is_complete=True,
                remaining_steps=0
            )
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
            if result:
                return result.to_dict()
            # 返回未匹配的结果
            return {
                "matched": False,
                "page": None,
                "available_actions": [],
                "candidates": []
            }
        else:
            response = self._http.post("/api/v1/query/match-page", json={
                "app_id": app_id,
                "ui_hierarchy": ui_hierarchy,
                "page_title": page_title
            })
            return response.json()
    
    def get_available_actions(self, page_id: str) -> Dict:
        """
        获取页面的所有可用操作
        
        Args:
            page_id: 页面ID
            
        Returns:
            符合API规范的操作列表
        """
        if self._is_local:
            page = self.graph.get_page(page_id)
            if not page:
                return {
                    "page_id": page_id,
                    "page_name": "",
                    "actions": [],
                    "total_count": 0
                }
            
            transitions = self.graph.get_outgoing_transitions(page_id)
            actions = []
            for t in transitions:
                target_page = self.graph.get_page(t.target_page_id)
                actions.append({
                    "action_type": t.action_type.value,
                    "widget_id": t.trigger_widget_id,
                    "widget_text": t.trigger_widget_text,
                    "target_page_id": t.target_page_id,
                    "target_page_name": target_page.page_name if target_page else "",
                    "success_rate": t.success_rate,
                    "avg_latency_ms": t.avg_latency_ms,
                    "description": f"{t.action_type.value} {t.trigger_widget_text}"
                })
            
            return {
                "page_id": page_id,
                "page_name": page.page_name,
                "actions": actions,
                "total_count": len(actions)
            }
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
            is_updated = False
            
            if transition:
                # 更新统计
                self.graph.update_transition_stats(
                    transition.transition_id,
                    success=success,
                    latency_ms=latency_ms
                )
                is_updated = True
                transition_id = transition.transition_id
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
                    fail_count=0 if success else 1,
                    avg_latency_ms=latency_ms
                )
                self.graph.add_transition(trans)
                transition_id = trans.transition_id
            
            # 返回符合API规范的格式
            updated_transition = self.graph.get_transition(from_page, to_page)
            if updated_transition:
                return {
                    "success": True,
                    "transition_id": transition_id,
                    "updated": is_updated,
                    "stats": {
                        "success_count": updated_transition.success_count,
                        "fail_count": updated_transition.fail_count,
                        "success_rate": updated_transition.success_rate,
                        "avg_latency_ms": updated_transition.avg_latency_ms
                    }
                }
            return {
                "success": True,
                "transition_id": transition_id,
                "updated": is_updated,
                "stats": {
                    "success_count": 0,
                    "fail_count": 0,
                    "success_rate": 0.0,
                    "avg_latency_ms": 0
                }
            }
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
        else:
            response = self._http.post("/api/v1/intent/register", json={
                "app_id": app_id,
                "intent_text": intent_text,
                "target_page": target_page,
                "keywords": keywords or []
            })
            data = response.json()
            intent_id = data.get("intent_id", intent_id)
        
        return intent_id
    
    def find_similar_intents(
        self,
        query: str,
        app_id: str = None,
        top_k: int = 5
    ) -> Dict:
        """
        查找相似意图
        
        Args:
            query: 查询文本
            app_id: 可选，限制在特定App内查找
            top_k: 返回前K个结果
            
        Returns:
            {
                "intents": [...],
                "total_found": int
            }
        """
        if self._is_local:
            # 编码查询文本
            query_vec = self.embedder.encode_single(query)
            
            # 搜索相似意图
            results = self.vectors.intents.search(query_vec, top_k=top_k)
            
            # 过滤app_id（如果指定）
            intents = []
            for r in results:
                metadata = r.metadata
                if app_id and metadata.get("app_id") != app_id:
                    continue
                
                intents.append({
                    "intent_id": r.id,
                    "intent_text": metadata.get("text", ""),
                    "app_id": metadata.get("app_id", ""),
                    "target_page": metadata.get("target_page_id", ""),
                    "similarity": r.score,
                    "keywords": metadata.get("keywords", [])
                })
            
            return {
                "intents": intents,
                "total_found": len(intents)
            }
        else:
            response = self._http.post("/api/v1/intent/find-similar", json={
                "query": query,
                "app_id": app_id,
                "top_k": top_k
            })
            return response.json()
    
    def batch_add_transitions(self, transitions: List[Dict]) -> Dict:
        """
        批量添加页面转换
        
        Args:
            transitions: 转换关系列表
            
        Returns:
            {
                "success": bool,
                "total": int,
                "created": int,
                "updated": int,
                "failed": int,
                "errors": [str]
            }
        """
        if self._is_local:
            created = 0
            updated = 0
            failed = 0
            errors = []
            
            for trans_data in transitions:
                try:
                    from_page = trans_data.get("from_page")
                    to_page = trans_data.get("to_page")
                    action_type = trans_data.get("action_type", "click")
                    widget_text = trans_data.get("widget_text", "")
                    
                    if not from_page or not to_page:
                        failed += 1
                        errors.append(f"缺少必要字段: {trans_data}")
                        continue
                    
                    # 检查转换是否已存在
                    existing = self.graph.get_transition(from_page, to_page)
                    
                    if existing:
                        # 更新统计
                        success_count = trans_data.get("success_count", 0)
                        fail_count = trans_data.get("fail_count", 0)
                        if success_count > 0 or fail_count > 0:
                            for _ in range(success_count):
                                self.graph.update_transition_stats(
                                    existing.transition_id, success=True
                                )
                            for _ in range(fail_count):
                                self.graph.update_transition_stats(
                                    existing.transition_id, success=False
                                )
                        updated += 1
                    else:
                        # 创建新转换
                        from kg_core.schema import Transition, ActionType
                        
                        transition = Transition(
                            transition_id=Transition.generate_id(
                                from_page, to_page, action_type
                            ),
                            source_page_id=from_page,
                            target_page_id=to_page,
                            trigger_widget_text=widget_text,
                            action_type=ActionType(action_type),
                            success_count=trans_data.get("success_count", 0),
                            fail_count=trans_data.get("fail_count", 0)
                        )
                        self.graph.add_transition(transition)
                        created += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"处理转换失败: {str(e)}")
            
            return {
                "success": failed == 0,
                "total": len(transitions),
                "created": created,
                "updated": updated,
                "failed": failed,
                "errors": errors
            }
        else:
            response = self._http.post("/api/v1/graph/batch-add-transitions", json={
                "transitions": transitions
            })
            return response.json()
    
    # ==================== 工具方法 ====================
    
    def get_graph_stats(self) -> Dict:
        """获取图谱统计信息（符合API规范）"""
        if self._is_local:
            stats = self.graph.get_graph_stats()
            # 转换为API规范格式
            from datetime import datetime
            return {
                "apps": stats.get("total_apps", 0),
                "pages": stats.get("total_pages", 0),
                "transitions": stats.get("total_transitions", 0),
                "intents": self.vectors.intents.count() if hasattr(self.vectors.intents, 'count') else 0,
                "avg_path_length": stats.get("avg_path_length", 0.0),
                "avg_success_rate": stats.get("avg_success_rate", 0.0),
                "last_updated": datetime.now().isoformat()
            }
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
