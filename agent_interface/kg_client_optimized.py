"""
知识图谱客户端 - 优化版

这是GUI Agent与知识图谱系统交互的主要接口

优化点:
- 消除本地/远程模式的代码重复，使用KGStore抽象
- 添加pydantic数据验证
- 改进错误处理
- 添加日志记录

使用方式:
    from agent_interface import KGClient

    kg = KGClient()

    # 查询操作路径
    result = kg.query_path("com.meituan.app", "查找附近餐厅")

    # 获取下一步操作
    action = kg.get_next_action("home_page", "查找附近餐厅")

    # 上报操作结果
    kg.report_transition(from_page, action, to_page, success=True)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_interface.kg_store import (
    KGStore, LocalKGStore, RemoteKGStore, PathQueryResult,
    PageMatchResult, ActionResult, create_kg_store
)

logger = logging.getLogger(__name__)


# ==================== Pydantic验证模型 ====================

class QueryPathRequest(BaseModel):
    """路径查询请求验证"""
    app_id: str = Field(..., min_length=1, description="应用ID")
    intent: str = Field(..., min_length=1, description="用户意图")
    current_page: Optional[str] = Field(None, description="当前页面ID")
    max_steps: int = Field(10, ge=1, le=100, description="最大步骤数")


class AddPageRequest(BaseModel):
    """添加页面请求验证"""
    app_id: str = Field(..., min_length=1)
    page_name: str = Field(..., min_length=1)
    page_type: str = Field("other", regex="^(home|list|detail|form|dialog|search|settings|other)$")
    description: str = Field("", max_length=1000)
    intents: Optional[List[str]] = Field(None)

    @validator('intents')
    def validate_intents(cls, v):
        if v and len(v) > 100:
            raise ValueError('Too many intents')
        return v


class RegisterIntentRequest(BaseModel):
    """注册意图请求验证"""
    app_id: str = Field(..., min_length=1)
    intent_text: str = Field(..., min_length=1)
    target_page: Optional[str] = Field(None)
    keywords: Optional[List[str]] = Field(None)


class ReportTransitionRequest(BaseModel):
    """上报转换请求验证"""
    from_page: str = Field(..., min_length=1)
    to_page: str = Field(..., min_length=1)
    action: Dict = Field(...)
    success: bool = Field(True)
    latency_ms: int = Field(0, ge=0)


# ==================== KGClient (简化版本) ====================

class KGClient:
    """
    知识图谱客户端 - 简化版

    使用KGStore抽象消除本地/远程模式的代码重复

    核心方法:
    - query_path(): 根据意图查询操作路径
    - get_next_action(): 获取下一步推荐操作
    - match_current_page(): 匹配当前页面
    - report_transition(): 上报页面转换（用于图谱学习）
    """

    def __init__(
        self,
        store: KGStore = None,
        mode: str = "local",
        api_endpoint: str = None,
        **local_kwargs
    ):
        """
        初始化客户端

        Args:
            store: KGStore实例（如果提供则使用，否则根据mode创建）
            mode: "local" 或 "remote"
            api_endpoint: API端点（remote模式需要）
            **local_kwargs: 本地模式的组件
        """
        if store:
            self.store = store
        else:
            self.store = self._create_store(mode, api_endpoint, **local_kwargs)

        logger.info(f"KGClient initialized with {self.store.__class__.__name__}")

    def _create_store(self, mode: str, api_endpoint: str = None, **local_kwargs) -> KGStore:
        """创建存储实例"""
        if mode == "remote":
            if not api_endpoint:
                raise ValueError("远程模式必须指定api_endpoint")
            return RemoteKGStore(api_endpoint)
        else:
            # 本地模式需要组件
            if not all(k in local_kwargs for k in ['graph_store', 'vector_store', 'embedding_model']):
                # 如果缺少组件，尝试导入default实现
                from kg_core.graph_store_optimized import MemoryGraphStore
                from kg_core.vector_store import VectorStoreManager
                from kg_core.embeddings import EmbeddingModel
                from kg_query.path_finder import PathFinder
                from kg_query.page_matcher import PageMatcher
                from kg_query.rag_engine import RAGEngine

                local_kwargs.setdefault('graph_store', MemoryGraphStore())
                local_kwargs.setdefault('vector_store', VectorStoreManager(mode="memory"))
                local_kwargs.setdefault('embedding_model', EmbeddingModel(use_mock=True))

                # 初始化查询引擎
                graph_store = local_kwargs['graph_store']
                vector_store = local_kwargs['vector_store']
                embedding_model = local_kwargs['embedding_model']

                local_kwargs.setdefault('path_finder', PathFinder(graph_store, vector_store, embedding_model))
                local_kwargs.setdefault('page_matcher', PageMatcher(graph_store, vector_store, embedding_model))
                local_kwargs.setdefault('rag_engine', RAGEngine(graph_store, vector_store, embedding_model))

            return LocalKGStore(**local_kwargs)

    # ==================== 查询接口 ====================

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
        """
        try:
            # 参数验证
            req = QueryPathRequest(
                app_id=app_id,
                intent=intent,
                current_page=current_page,
                max_steps=max_steps
            )

            result: PathQueryResult = self.store.query_path(
                app_id=req.app_id,
                intent=req.intent,
                current_page=req.current_page,
                max_steps=req.max_steps
            )

            logger.info(f"Query path: {app_id} -> {intent} (success={result.success})")
            return result.to_dict()

        except ValueError as e:
            logger.error(f"Invalid parameters: {e}")
            return {
                "success": False,
                "message": f"参数验证失败: {str(e)}",
                "path": None,
                "alternatives": []
            }
        except Exception as e:
            logger.error(f"Error querying path: {e}")
            return {
                "success": False,
                "message": f"查询失败: {str(e)}",
                "path": None,
                "alternatives": []
            }

    def get_next_action(
        self,
        current_page: str,
        intent: str,
        app_id: str = ""
    ) -> Optional[Dict]:
        """
        获取下一步推荐操作

        用于Agent的实时决策，只返回立即需要执行的操作

        Args:
            current_page: 当前页面ID
            intent: 目标意图
            app_id: 应用ID

        Returns:
            操作推荐或None
        """
        try:
            action_result: ActionResult = self.store.get_next_action(
                current_page=current_page,
                intent=intent,
                app_id=app_id
            )

            if action_result:
                logger.debug(f"Next action: {action_result.action_type} on {action_result.widget_text}")
                return action_result.to_dict()

            return None

        except Exception as e:
            logger.error(f"Error getting next action: {e}")
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
            匹配结果
        """
        try:
            result: PageMatchResult = self.store.match_current_page(
                app_id=app_id,
                ui_hierarchy=ui_hierarchy,
                page_title=page_title
            )

            logger.debug(f"Page match: {app_id} -> confidence={result.confidence}")
            return result.to_dict()

        except Exception as e:
            logger.error(f"Error matching page: {e}")
            return {
                "matched": False,
                "page": None,
                "confidence": 0.0,
                "candidates": [],
                "available_actions": []
            }

    def get_available_actions(self, page_id: str) -> Dict:
        """
        获取页面的所有可用操作

        Args:
            page_id: 页面ID

        Returns:
            符合API规范的操作列表
        """
        try:
            return self.store.get_available_actions(page_id)
        except Exception as e:
            logger.error(f"Error getting available actions: {e}")
            return {
                "page_id": page_id,
                "page_name": "",
                "actions": [],
                "total_count": 0
            }

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
        try:
            return self.store.get_rag_context(
                app_id=app_id,
                query=query,
                current_page=current_page
            )
        except Exception as e:
            logger.error(f"Error getting RAG context: {e}")
            return {
                "success": False,
                "message": f"获取上下文失败: {str(e)}",
                "context": []
            }

    # ==================== 图谱更新接口 ====================

    def report_transition(
        self,
        from_page: str,
        action: Dict,
        to_page: str,
        success: bool = True,
        latency_ms: int = 0
    ) -> Dict:
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
        try:
            # 参数验证
            req = ReportTransitionRequest(
                from_page=from_page,
                to_page=to_page,
                action=action,
                success=success,
                latency_ms=latency_ms
            )

            result = self.store.report_transition(
                from_page=req.from_page,
                action=req.action,
                to_page=req.to_page,
                success=req.success,
                latency_ms=req.latency_ms
            )

            logger.debug(f"Reported transition: {from_page} -> {to_page} (success={success})")
            return result

        except ValueError as e:
            logger.error(f"Invalid transition data: {e}")
            return {
                "success": False,
                "message": f"数据验证失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error reporting transition: {e}")
            return {
                "success": False,
                "message": f"上报失败: {str(e)}"
            }

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
        try:
            req = AddPageRequest(
                app_id=app_id,
                page_name=page_name,
                page_type=page_type,
                description=description,
                intents=intents
            )

            page_id = self.store.add_page(
                app_id=req.app_id,
                page_name=req.page_name,
                page_type=req.page_type,
                description=req.description,
                intents=req.intents,
                ui_hierarchy=ui_hierarchy
            )

            logger.info(f"Added page: {page_id} ({page_name})")
            return page_id

        except ValueError as e:
            logger.error(f"Invalid page data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding page: {e}")
            raise

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
        try:
            req = RegisterIntentRequest(
                app_id=app_id,
                intent_text=intent_text,
                target_page=target_page,
                keywords=keywords
            )

            intent_id = self.store.register_intent(
                app_id=req.app_id,
                intent_text=req.intent_text,
                target_page=req.target_page,
                keywords=req.keywords
            )

            logger.info(f"Registered intent: {intent_id}")
            return intent_id

        except ValueError as e:
            logger.error(f"Invalid intent data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error registering intent: {e}")
            raise

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
            相似意图列表
        """
        try:
            return self.store.find_similar_intents(
                query=query,
                app_id=app_id,
                top_k=top_k
            )
        except Exception as e:
            logger.error(f"Error finding similar intents: {e}")
            return {"intents": [], "total_found": 0}

    def batch_add_transitions(self, transitions: List[Dict]) -> Dict:
        """
        批量添加页面转换

        Args:
            transitions: 转换关系列表

        Returns:
            批量操作结果
        """
        try:
            return self.store.batch_add_transitions(transitions)
        except Exception as e:
            logger.error(f"Error batch adding transitions: {e}")
            return {
                "success": False,
                "total": len(transitions),
                "created": 0,
                "updated": 0,
                "failed": len(transitions),
                "errors": [str(e)]
            }

    # ==================== 工具方法 ====================

    def get_graph_stats(self) -> Dict:
        """获取图谱统计信息"""
        try:
            return self.store.get_graph_stats()
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {}

    def export_graph(self) -> Dict:
        """导出图谱数据"""
        try:
            return self.store.export_graph()
        except Exception as e:
            logger.error(f"Error exporting graph: {e}")
            return {}

    def clear_graph(self):
        """清空图谱（谨慎使用）"""
        try:
            self.store.clear_graph()
            logger.warning("Graph cleared")
        except Exception as e:
            logger.error(f"Error clearing graph: {e}")
            raise


# ==================== 便捷函数 ====================

def create_client(
    mode: str = "local",
    api_endpoint: str = None,
    **kwargs
) -> KGClient:
    """
    创建客户端实例

    Args:
        mode: "local" 或 "remote"
        api_endpoint: 远程API地址
        **kwargs: 其他参数

    Returns:
        KGClient实例
    """
    return KGClient(mode=mode, api_endpoint=api_endpoint, **kwargs)
