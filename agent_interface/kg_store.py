"""
KGStore 抽象接口层

分离本地和远程实现，消除kg_client中的重复代码
使用策略模式和工厂模式提供统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PathQueryResult:
    """路径查询结果"""
    success: bool
    path: Optional[Dict] = None
    alternatives: Optional[List[Dict]] = None
    message: str = ""

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "path": self.path,
            "alternatives": self.alternatives,
            "message": self.message
        }


@dataclass
class PageMatchResult:
    """页面匹配结果"""
    matched: bool
    page: Optional[Dict] = None
    confidence: float = 0.0
    candidates: Optional[List[Dict]] = None
    available_actions: Optional[List[Dict]] = None

    def to_dict(self) -> Dict:
        return {
            "matched": self.matched,
            "page": self.page,
            "confidence": self.confidence,
            "candidates": self.candidates or [],
            "available_actions": self.available_actions or []
        }


@dataclass
class ActionResult:
    """操作推荐结果"""
    action_type: str
    widget_id: str
    widget_text: str
    confidence: float = 0.0
    expected_page: str = ""
    description: str = ""
    is_complete: bool = False
    remaining_steps: int = 0

    def to_dict(self) -> Dict:
        if self.is_complete:
            return {
                "action": None,
                "is_complete": True,
                "remaining_steps": 0
            }

        return {
            "action": {
                "action_type": self.action_type,
                "widget_id": self.widget_id,
                "widget_text": self.widget_text,
                "confidence": self.confidence,
                "expected_page": self.expected_page,
                "description": self.description
            },
            "is_complete": self.is_complete,
            "remaining_steps": self.remaining_steps
        }


class KGStore(ABC):
    """知识图谱存储抽象基类

    统一本地和远程实现的接口，消除KGClient中的条件分支
    """

    # ==================== 查询接口 ====================

    @abstractmethod
    def query_path(
        self,
        app_id: str,
        intent: str,
        current_page: Optional[str] = None,
        max_steps: int = 10
    ) -> PathQueryResult:
        """查询操作路径"""
        pass

    @abstractmethod
    def get_next_action(
        self,
        current_page: str,
        intent: str,
        app_id: str = ""
    ) -> Optional[ActionResult]:
        """获取下一步推荐操作"""
        pass

    @abstractmethod
    def match_current_page(
        self,
        app_id: str,
        ui_hierarchy: Optional[Dict] = None,
        page_title: Optional[str] = None
    ) -> PageMatchResult:
        """匹配当前页面"""
        pass

    @abstractmethod
    def get_available_actions(self, page_id: str) -> Dict:
        """获取页面的可用操作"""
        pass

    @abstractmethod
    def get_rag_context(
        self,
        app_id: str,
        query: str,
        current_page: Optional[str] = None
    ) -> Dict:
        """获取RAG上下文"""
        pass

    # ==================== 图谱更新接口 ====================

    @abstractmethod
    def report_transition(
        self,
        from_page: str,
        action: Dict,
        to_page: str,
        success: bool = True,
        latency_ms: int = 0
    ) -> Dict:
        """上报页面转换"""
        pass

    @abstractmethod
    def add_page(
        self,
        app_id: str,
        page_name: str,
        page_type: str = "other",
        description: str = "",
        intents: Optional[List[str]] = None,
        ui_hierarchy: Optional[Dict] = None
    ) -> str:
        """添加新页面"""
        pass

    @abstractmethod
    def register_intent(
        self,
        app_id: str,
        intent_text: str,
        target_page: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> str:
        """注册新意图"""
        pass

    @abstractmethod
    def batch_add_transitions(self, transitions: List[Dict]) -> Dict:
        """批量添加页面转换"""
        pass

    # ==================== 工具方法 ====================

    @abstractmethod
    def get_graph_stats(self) -> Dict:
        """获取图谱统计信息"""
        pass

    @abstractmethod
    def export_graph(self) -> Dict:
        """导出图谱数据"""
        pass

    @abstractmethod
    def clear_graph(self):
        """清空图谱"""
        pass

    @abstractmethod
    def find_similar_intents(
        self,
        query: str,
        app_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict:
        """查找相似意图"""
        pass


class LocalKGStore(KGStore):
    """本地内存存储实现

    使用MemoryGraphStore + VectorStoreManager的组合
    """

    def __init__(
        self,
        graph_store,
        vector_store,
        embedding_model,
        path_finder,
        page_matcher,
        rag_engine
    ):
        self.graph = graph_store
        self.vectors = vector_store
        self.embedder = embedding_model
        self.path_finder = path_finder
        self.page_matcher = page_matcher
        self.rag_engine = rag_engine
        logger.info("LocalKGStore initialized")

    def query_path(
        self,
        app_id: str,
        intent: str,
        current_page: Optional[str] = None,
        max_steps: int = 10
    ) -> PathQueryResult:
        result = self.path_finder.find_path_by_intent(
            app_id=app_id,
            intent=intent,
            current_page_id=current_page,
            max_steps=max_steps
        )
        return PathQueryResult(
            success=result.get("success", False),
            path=result.get("path"),
            alternatives=result.get("alternatives"),
            message=result.get("message", "")
        )

    def get_next_action(
        self,
        current_page: str,
        intent: str,
        app_id: str = ""
    ) -> Optional[ActionResult]:
        next_action = self.path_finder.get_next_action(current_page, intent)
        if next_action:
            remaining_steps = next_action.get("remaining_steps", 0)
            is_complete = remaining_steps == 0

            return ActionResult(
                action_type=next_action.get("action_type", "click"),
                widget_id=next_action.get("widget_id", ""),
                widget_text=next_action.get("widget_text", ""),
                confidence=next_action.get("confidence", 0.0),
                expected_page=next_action.get("expected_page", ""),
                description=next_action.get("description", ""),
                is_complete=is_complete,
                remaining_steps=remaining_steps
            )

        return ActionResult(
            action_type="",
            widget_id="",
            widget_text="",
            is_complete=True,
            remaining_steps=0
        )

    def match_current_page(
        self,
        app_id: str,
        ui_hierarchy: Optional[Dict] = None,
        page_title: Optional[str] = None
    ) -> PageMatchResult:
        result = self.page_matcher.match_page(
            app_id=app_id,
            ui_hierarchy=ui_hierarchy,
            page_title=page_title
        )
        if result:
            return PageMatchResult(
                matched=True,
                page=result.to_dict(),
                confidence=result.confidence,
                available_actions=result.available_actions,
                candidates=result.candidates
            )

        return PageMatchResult(matched=False)

    def get_available_actions(self, page_id: str) -> Dict:
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
                "avg_latency_ms": t.avg_latency_ms
            })

        return {
            "page_id": page_id,
            "page_name": page.page_name,
            "actions": actions,
            "total_count": len(actions)
        }

    def get_rag_context(
        self,
        app_id: str,
        query: str,
        current_page: Optional[str] = None
    ) -> Dict:
        context = self.rag_engine.retrieve(
            app_id=app_id,
            query=query,
            current_page_id=current_page
        )
        return context.to_dict()

    def report_transition(
        self,
        from_page: str,
        action: Dict,
        to_page: str,
        success: bool = True,
        latency_ms: int = 0
    ) -> Dict:
        from kg_core.schema import Transition, ActionType

        transition = self.graph.get_transition(from_page, to_page)
        is_updated = False

        if transition:
            self.graph.update_transition_stats(
                transition.transition_id,
                success=success,
                latency_ms=latency_ms
            )
            is_updated = True
            transition_id = transition.transition_id
        else:
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
            "stats": {"success_count": 0, "fail_count": 0, "success_rate": 0.0, "avg_latency_ms": 0}
        }

    def add_page(
        self,
        app_id: str,
        page_name: str,
        page_type: str = "other",
        description: str = "",
        intents: Optional[List[str]] = None,
        ui_hierarchy: Optional[Dict] = None
    ) -> str:
        from kg_core.schema import Page, PageType

        page_id = Page.generate_id(app_id, page_name)
        page = Page(
            page_id=page_id,
            page_name=page_name,
            app_id=app_id,
            page_type=PageType(page_type),
            description=description,
            intents=intents or []
        )

        self.graph.add_page(page)
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
        target_page: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> str:
        from kg_core.schema import Intent

        intent_id = Intent.generate_id(app_id, intent_text)
        vec = self.embedder.encode_single(intent_text)

        self.vectors.intents.insert(intent_id, vec, {
            "text": intent_text,
            "app_id": app_id,
            "target_page_id": target_page,
            "keywords": keywords or []
        })

        return intent_id

    def batch_add_transitions(self, transitions: List[Dict]) -> Dict:
        from kg_core.schema import Transition, ActionType

        created = 0
        updated = 0
        failed = 0
        errors = []

        for trans_data in transitions:
            try:
                from_page = trans_data.get("from_page")
                to_page = trans_data.get("to_page")
                action_type = trans_data.get("action_type", "click")

                if not from_page or not to_page:
                    failed += 1
                    errors.append(f"缺少必要字段: {trans_data}")
                    continue

                existing = self.graph.get_transition(from_page, to_page)

                if existing:
                    success_count = trans_data.get("success_count", 0)
                    fail_count = trans_data.get("fail_count", 0)
                    if success_count > 0 or fail_count > 0:
                        for _ in range(success_count):
                            self.graph.update_transition_stats(existing.transition_id, success=True)
                        for _ in range(fail_count):
                            self.graph.update_transition_stats(existing.transition_id, success=False)
                    updated += 1
                else:
                    transition = Transition(
                        transition_id=Transition.generate_id(from_page, to_page, action_type),
                        source_page_id=from_page,
                        target_page_id=to_page,
                        trigger_widget_text=trans_data.get("widget_text", ""),
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

    def get_graph_stats(self) -> Dict:
        stats = self.graph.get_graph_stats()
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

    def export_graph(self) -> Dict:
        return self.graph.export_to_dict()

    def clear_graph(self):
        self.graph.clear()
        self.vectors.pages.clear()
        self.vectors.intents.clear()

    def find_similar_intents(
        self,
        query: str,
        app_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict:
        query_vec = self.embedder.encode_single(query)
        results = self.vectors.intents.search(query_vec, top_k=top_k)

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

        return {"intents": intents, "total_found": len(intents)}


class RemoteKGStore(KGStore):
    """远程API存储实现

    通过HTTP调用远程知识图谱服务
    """

    def __init__(self, api_endpoint: str):
        try:
            import httpx
            self._http = httpx.Client(base_url=api_endpoint, timeout=30.0)
        except ImportError:
            raise ImportError("远程模式需要安装httpx: pip install httpx")
        self.api_endpoint = api_endpoint
        logger.info(f"RemoteKGStore initialized with endpoint: {api_endpoint}")

    def query_path(
        self,
        app_id: str,
        intent: str,
        current_page: Optional[str] = None,
        max_steps: int = 10
    ) -> PathQueryResult:
        response = self._http.post("/api/v1/query/path", json={
            "app_id": app_id,
            "intent": intent,
            "current_page_id": current_page,
            "max_steps": max_steps
        })
        data = response.json()
        return PathQueryResult(
            success=data.get("success", False),
            path=data.get("path"),
            alternatives=data.get("alternatives"),
            message=data.get("message", "")
        )

    def get_next_action(
        self,
        current_page: str,
        intent: str,
        app_id: str = ""
    ) -> Optional[ActionResult]:
        response = self._http.post("/api/v1/query/next-action", json={
            "current_page_id": current_page,
            "intent": intent,
            "app_id": app_id
        })
        data = response.json()
        if data.get("action"):
            return ActionResult(**data["action"])
        return None

    def match_current_page(
        self,
        app_id: str,
        ui_hierarchy: Optional[Dict] = None,
        page_title: Optional[str] = None
    ) -> PageMatchResult:
        response = self._http.post("/api/v1/query/match-page", json={
            "app_id": app_id,
            "ui_hierarchy": ui_hierarchy,
            "page_title": page_title
        })
        data = response.json()
        return PageMatchResult(
            matched=data.get("matched", False),
            page=data.get("page"),
            confidence=data.get("confidence", 0.0),
            candidates=data.get("candidates"),
            available_actions=data.get("available_actions")
        )

    def get_available_actions(self, page_id: str) -> Dict:
        response = self._http.get(f"/api/v1/pages/{page_id}/actions")
        return response.json()

    def get_rag_context(
        self,
        app_id: str,
        query: str,
        current_page: Optional[str] = None
    ) -> Dict:
        response = self._http.post("/api/v1/rag/retrieve", json={
            "app_id": app_id,
            "query": query,
            "current_page_id": current_page
        })
        return response.json()

    def report_transition(
        self,
        from_page: str,
        action: Dict,
        to_page: str,
        success: bool = True,
        latency_ms: int = 0
    ) -> Dict:
        response = self._http.post("/api/v1/graph/report-transition", json={
            "from_page": from_page,
            "action": action,
            "to_page": to_page,
            "success": success,
            "latency_ms": latency_ms
        })
        return response.json()

    def add_page(
        self,
        app_id: str,
        page_name: str,
        page_type: str = "other",
        description: str = "",
        intents: Optional[List[str]] = None,
        ui_hierarchy: Optional[Dict] = None
    ) -> str:
        response = self._http.post("/api/v1/pages/add", json={
            "app_id": app_id,
            "page_name": page_name,
            "page_type": page_type,
            "description": description,
            "intents": intents or [],
            "ui_hierarchy": ui_hierarchy
        })
        data = response.json()
        return data.get("page_id", "")

    def register_intent(
        self,
        app_id: str,
        intent_text: str,
        target_page: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> str:
        response = self._http.post("/api/v1/intent/register", json={
            "app_id": app_id,
            "intent_text": intent_text,
            "target_page": target_page,
            "keywords": keywords or []
        })
        data = response.json()
        return data.get("intent_id", "")

    def batch_add_transitions(self, transitions: List[Dict]) -> Dict:
        response = self._http.post("/api/v1/graph/batch-add-transitions", json={
            "transitions": transitions
        })
        return response.json()

    def get_graph_stats(self) -> Dict:
        response = self._http.get("/api/v1/graph/stats")
        return response.json()

    def export_graph(self) -> Dict:
        response = self._http.get("/api/v1/graph/export")
        return response.json()

    def clear_graph(self):
        self._http.post("/api/v1/graph/clear")

    def find_similar_intents(
        self,
        query: str,
        app_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict:
        response = self._http.post("/api/v1/intent/find-similar", json={
            "query": query,
            "app_id": app_id,
            "top_k": top_k
        })
        return response.json()


def create_kg_store(
    mode: str = "local",
    api_endpoint: str = None,
    **local_kwargs
) -> KGStore:
    """工厂函数：创建KGStore实例

    Args:
        mode: "local" 或 "remote"
        api_endpoint: 远程API地址（remote模式需要）
        **local_kwargs: 本地模式的组件（graph_store, vector_store等）

    Returns:
        KGStore实现实例
    """
    if mode == "remote":
        if not api_endpoint:
            raise ValueError("远程模式必须指定api_endpoint")
        return RemoteKGStore(api_endpoint)
    else:
        return LocalKGStore(**local_kwargs)
