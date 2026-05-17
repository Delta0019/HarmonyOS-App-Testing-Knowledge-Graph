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

from kg_core.schema import Page, Widget, Transition, ActionType, PageType, WidgetType
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
        page_title: str = None,
        activity: str = "",
    ) -> Optional[Dict]:
        """
        匹配当前页面

        根据UI结构或标题匹配图谱中的页面

        Args:
            app_id: 应用ID
            ui_hierarchy: UI控件树
            page_title: 页面标题
            activity: Android Activity 名

        Returns:
            {
                "matched": True/False,
                "page": {"page_id": ..., "page_name": ..., "confidence": ...},
                ...
            }
        """
        if self._is_local:
            # 先尝试用 structural_fingerprint 直接查找
            if ui_hierarchy and hasattr(self.graph, "find_page_by_fingerprint"):
                widgets_data = []
                for child in ui_hierarchy.get("children", []):
                    widgets_data.append({
                        "class_name": child.get("class_name") or child.get("class", ""),
                        "resource_id": child.get("resource-id") or child.get("resource_id", ""),
                    })
                fp = Page.compute_structural_fingerprint(app_id, activity, widgets_data)
                found = self.graph.find_page_by_fingerprint(fp, app_id)
                if found:
                    # 更新访问信息
                    found.visit_count += 1
                    transitions = self.graph.get_outgoing_transitions(found.page_id)
                    actions = []
                    for t in transitions:
                        tp = self.graph.get_page(t.target_page_id)
                        actions.append({
                            "widget_text": t.trigger_widget_text,
                            "action": t.action_type.value,
                            "leads_to": tp.page_name if tp else t.target_page_id,
                            "success_rate": t.success_rate,
                        })
                    return {
                        "matched": True,
                        "page": {
                            "page_id": found.page_id,
                            "page_name": found.page_name,
                            "confidence": 1.0,
                        },
                        "available_actions": actions,
                    }

            # fallback 到 PageMatcher（语义 + 结构混合匹配）
            result = self.page_matcher.match_page(
                app_id=app_id,
                ui_hierarchy=ui_hierarchy,
                page_title=page_title,
                activity=activity,
            )
            if result and result.page_id and result.confidence > 0:
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
            # 提取 widget 标识
            widget_rid = action.get("widget_resource_id", action.get("widget", ""))
            widget_text = action.get("widget_text", "")
            action_type_str = action.get("type", "click")

            # 用 find_matching_transition 精确匹配（按 widget 区分）
            transition = None
            if hasattr(self.graph, "find_matching_transition"):
                transition = self.graph.find_matching_transition(
                    from_page, to_page, action_type_str, widget_rid, widget_text
                )
            if not transition:
                transition = self.graph.get_transition(from_page, to_page)
            is_updated = False

            if transition:
                self.graph.update_transition_stats(
                    transition.transition_id,
                    success=success,
                    latency_ms=latency_ms
                )
                # 补充 widget 信息（可能旧转换缺失这些字段）
                if not transition.trigger_widget_class and action.get("widget_class"):
                    transition.trigger_widget_class = action["widget_class"]
                if not transition.trigger_widget_resource_id and widget_rid:
                    transition.trigger_widget_resource_id = widget_rid
                center = action.get("widget_center", ())
                if center and not transition.trigger_widget_center:
                    transition.trigger_widget_center = tuple(center) if isinstance(center, (list, tuple)) else ()
                if action.get("input_text") and not transition.input_text:
                    transition.input_text = action["input_text"]
                is_updated = True
                transition_id = transition.transition_id
            else:
                # 安全解析 action_type
                try:
                    at_enum = ActionType(action_type_str)
                except ValueError:
                    at_enum = ActionType.CLICK
                center = action.get("widget_center", ())
                if isinstance(center, list):
                    center = tuple(center)

                trans = Transition(
                    transition_id=Transition.generate_id(
                        from_page, to_page, action_type_str,
                        widget_key=widget_rid or widget_text,
                    ),
                    source_page_id=from_page,
                    target_page_id=to_page,
                    trigger_widget_id=action.get("widget", ""),
                    trigger_widget_text=widget_text,
                    trigger_widget_class=action.get("widget_class", ""),
                    trigger_widget_resource_id=widget_rid,
                    trigger_widget_center=center,
                    action_type=at_enum,
                    input_text=action.get("input_text", ""),
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
        添加新页面到图谱，自动从 ui_hierarchy 提取 widgets 和结构指纹。

        Returns:
            页面ID
        """
        # 从 ui_hierarchy 提取 widgets 和状态哈希
        state_hash = ""
        structural_fingerprint = ""
        widgets = []

        if ui_hierarchy:
            state_hash = Page.compute_state_hash(ui_hierarchy)

        page_id = Page.generate_id(app_id, page_name, state_hash)

        if ui_hierarchy:
            widgets = self._extract_widgets(ui_hierarchy, page_id)
            # 将 children 作为 widgets_data 传入计算结构指纹
            widgets_data = ui_hierarchy.get("children", [])
            if widgets_data:
                structural_fingerprint = Page.compute_structural_fingerprint(
                    app_id, "", widgets_data
                )

        page = Page(
            page_id=page_id,
            page_name=page_name,
            app_id=app_id,
            page_type=PageType(page_type),
            state_hash=state_hash,
            structural_fingerprint=structural_fingerprint,
            description=description,
            intents=intents or [],
            widgets=widgets,
        )

        if self._is_local:
            self.graph.add_page(page)

            # 生成更完整的向量嵌入（合并 page_name + description + intents）
            text_parts = [page_name]
            if description:
                text_parts.append(description)
            if intents:
                text_parts.extend(intents)
            combined_text = " ".join(text_parts)

            vec = self.embedder.encode_single(combined_text)
            self.vectors.pages.insert(page_id, vec, {
                "name": page_name,
                "description": description,
                "intents": intents or []
            })

        return page_id

    # ---- Widget 提取辅助方法 ----

    @staticmethod
    def _extract_widgets(ui_hierarchy: Dict, page_id: str) -> List[Widget]:
        """从 UI 层次结构提取可交互控件。"""
        widgets = []

        def traverse(node, xpath=""):
            if not isinstance(node, dict):
                return

            current_xpath = f"{xpath}/{node.get('class', 'unknown')}"

            is_interactive = (
                node.get("clickable", False)
                or node.get("scrollable", False)
                or node.get("editable", False)
            )

            if is_interactive:
                widget_id = Widget.generate_id(page_id, current_xpath)
                widget = Widget(
                    widget_id=widget_id,
                    widget_type=KGClient._infer_widget_type(node),
                    text=node.get("text", ""),
                    content_desc=node.get("content-desc", ""),
                    resource_id=node.get("resource-id", ""),
                    xpath=current_xpath,
                    bounds=node.get("bounds", {}),
                    is_clickable=node.get("clickable", False),
                    is_scrollable=node.get("scrollable", False),
                    is_editable=node.get("editable", False),
                )
                widgets.append(widget)

            for i, child in enumerate(node.get("children", [])):
                traverse(child, f"{current_xpath}[{i}]")

        traverse(ui_hierarchy)
        return widgets

    @staticmethod
    def _infer_widget_type(node: Dict) -> WidgetType:
        """推断控件类型。"""
        class_name = node.get("class", "").lower()
        if "button" in class_name:
            return WidgetType.BUTTON
        elif "edittext" in class_name or "input" in class_name:
            return WidgetType.INPUT
        elif "textview" in class_name or "text" in class_name:
            return WidgetType.TEXT
        elif "imageview" in class_name or "image" in class_name:
            return WidgetType.IMAGE
        elif "listview" in class_name or "recyclerview" in class_name:
            return WidgetType.LIST
        elif "checkbox" in class_name:
            return WidgetType.CHECKBOX
        elif "switch" in class_name:
            return WidgetType.SWITCH
        else:
            return WidgetType.OTHER
    
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
    
    def save(self, directory: str):
        """持久化 KG 数据（graph + vectors）到目录。"""
        import json, os
        os.makedirs(directory, exist_ok=True)

        # 保存图谱
        graph_path = os.path.join(directory, "graph.json")
        self.graph.save_to_json(graph_path)

        # 保存向量（pages + intents）
        vectors_path = os.path.join(directory, "vectors.json")
        vec_data = {}
        for store_name in ("pages", "intents"):
            store = self.vectors.get_store(store_name)
            entries = {}
            for vid, vec in store.vectors.items():
                entries[vid] = {
                    "vector": vec.tolist(),
                    "metadata": store.metadata.get(vid, {}),
                }
            vec_data[store_name] = entries

        with open(vectors_path, "w", encoding="utf-8") as f:
            json.dump(vec_data, f, ensure_ascii=False)

        print(f"[KG] 已保存到 {directory} "
              f"(pages={len(self.graph.pages)}, "
              f"transitions={len(self.graph.transitions)})")

    def load(self, directory: str):
        """从目录加载 KG 数据。"""
        import json, os

        graph_path = os.path.join(directory, "graph.json")
        if os.path.exists(graph_path):
            self.graph.load_from_json(graph_path)

        vectors_path = os.path.join(directory, "vectors.json")
        if os.path.exists(vectors_path):
            with open(vectors_path, "r", encoding="utf-8") as f:
                vec_data = json.load(f)

            for store_name in ("pages", "intents"):
                store = self.vectors.get_store(store_name)
                for vid, entry in vec_data.get(store_name, {}).items():
                    store.insert(vid, entry["vector"], entry.get("metadata", {}))

        print(f"[KG] 已加载 {directory} "
              f"(pages={len(self.graph.pages)}, "
              f"transitions={len(self.graph.transitions)})")

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
