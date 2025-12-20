"""
路径查询模块

提供基于图结构的路径查询能力:
- 最短路径查询
- 多路径查询
- 基于意图的路径检索
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from kg_core.schema import Page, ActionStep, ActionPath, ActionType
from kg_core.graph_store import BaseGraphStore, PathResult
from kg_core.vector_store import VectorStoreManager, SearchResult
from kg_core.embeddings import EmbeddingModel


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    path: Optional[ActionPath] = None
    alternatives: List[ActionPath] = None
    message: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为符合API规范的字典格式"""
        result = {
            "success": self.success,
            "message": self.message,
            "confidence": self.confidence
        }
        
        if self.path:
            path_dict = self.path.to_dict()
            result["path"] = path_dict
            
            # 添加目标页面信息（如果可用）
            if hasattr(self, 'target_page') and self.target_page:
                result["target_page"] = self.target_page
        
        if self.alternatives:
            result["alternatives"] = [
                {
                    "total_steps": alt.total_steps,
                    "confidence": alt.confidence,
                    "steps": [s.to_dict() for s in alt.steps],
                    "reason": getattr(alt, 'reason', '备选路径')
                }
                for alt in self.alternatives
            ]
        
        return result


class PathFinder:
    """
    路径查询器
    
    结合图结构和向量检索实现智能路径查询
    """
    
    def __init__(
        self,
        graph_store: BaseGraphStore,
        vector_store: VectorStoreManager,
        embedding_model: EmbeddingModel
    ):
        self.graph = graph_store
        self.vectors = vector_store
        self.embedder = embedding_model
    
    def find_path_by_intent(
        self,
        app_id: str,
        intent: str,
        current_page_id: str = None,
        max_steps: int = 10
    ) -> QueryResult:
        """
        根据意图查找操作路径
        
        流程:
        1. 编码意图为向量
        2. 在意图库中搜索相似意图
        3. 获取关联的目标页面
        4. 查找到目标页面的路径
        """
        # 1. 编码意图
        intent_vec = self.embedder.encode_single(intent)
        
        # 2. 搜索相似意图
        similar_intents = self.vectors.intents.search(intent_vec, top_k=3)
        
        # 3. 确定起始页面
        if not current_page_id:
            # 默认从首页开始
            home_page = self.graph.find_page_by_name("首页", app_id)
            if home_page:
                current_page_id = home_page.page_id
            else:
                return QueryResult(
                    success=False,
                    message="无法确定起始页面"
                )
        
        # 4. 尝试找到目标页面
        target_page_id = None
        confidence = 0.0
        
        if similar_intents:
            best_match = similar_intents[0]
            confidence = best_match.score
            target_page_id = best_match.metadata.get("target_page_id")
        
        # 5. 如果没有匹配的意图，尝试基于页面描述搜索
        if not target_page_id:
            page_results = self.vectors.pages.search(intent_vec, top_k=3)
            if page_results:
                target_page_id = page_results[0].id
                confidence = page_results[0].score
        
        if not target_page_id:
            return QueryResult(
                success=False,
                message=f"未找到与意图'{intent}'匹配的目标页面"
            )
        
        # 6. 查找路径
        path_result = self.graph.find_shortest_path(current_page_id, target_page_id)
        
        if not path_result:
            return QueryResult(
                success=False,
                message=f"从当前页面到目标页面不可达"
            )
        
        # 7. 构建ActionPath
        action_path = self._build_action_path(intent, path_result)
        action_path.confidence = confidence
        
        # 获取目标页面信息
        target_page = self.graph.get_page(target_page_id)
        target_page_info = None
        if target_page:
            target_page_info = {
                "page_id": target_page.page_id,
                "page_name": target_page.page_name,
                "page_type": target_page.page_type.value,
                "description": target_page.description
            }
        
        # 8. 查找备选路径
        alternatives = []
        all_paths = self.graph.find_all_paths(current_page_id, target_page_id, max_steps)
        for pr in all_paths[1:3]:  # 最多2条备选
            alt_path = self._build_action_path(intent, pr)
            alt_path.confidence = confidence * 0.8  # 备选路径置信度稍低
            # 添加备选原因
            alt_path.reason = "路径更短但成功率较低" if pr.total_steps < path_result.total_steps else "备选路径"
            alternatives.append(alt_path)
        
        result = QueryResult(
            success=True,
            path=action_path,
            alternatives=alternatives,
            confidence=confidence,
            message=f"找到路径，共{action_path.total_steps}步"
        )
        # 添加目标页面信息到结果对象
        result.target_page = target_page_info
        
        return result
    
    def find_path_direct(
        self,
        start_page_id: str,
        end_page_id: str
    ) -> QueryResult:
        """直接查找两个页面之间的路径"""
        path_result = self.graph.find_shortest_path(start_page_id, end_page_id)
        
        if not path_result:
            return QueryResult(
                success=False,
                message="路径不存在"
            )
        
        action_path = self._build_action_path("direct_navigation", path_result)
        
        return QueryResult(
            success=True,
            path=action_path,
            confidence=1.0
        )
    
    def get_next_action(
        self,
        current_page_id: str,
        target_intent: str
    ) -> Optional[Dict]:
        """
        获取下一步推荐操作
        
        用于实时Agent决策，只返回下一步
        """
        result = self.find_path_by_intent(
            app_id="",  # 从current_page推断
            intent=target_intent,
            current_page_id=current_page_id
        )
        
        if result.success and result.path and result.path.steps:
            first_step = result.path.steps[0]
            return {
                "action": first_step.action_type.value,
                "widget_id": first_step.target_widget_id,
                "widget_text": first_step.target_widget_text,
                "description": first_step.description,
                "expected_page": first_step.expected_page_id,
                "remaining_steps": result.path.total_steps - 1
            }
        return None
    
    def get_reachable_intents(self, current_page_id: str) -> List[str]:
        """获取从当前页面可达的所有意图"""
        reachable_pages = self.graph.get_reachable_pages(current_page_id)
        intents = []
        
        for page_id in reachable_pages:
            page = self.graph.get_page(page_id)
            if page and page.intents:
                intents.extend(page.intents)
        
        return list(set(intents))
    
    def _build_action_path(self, intent: str, path_result: PathResult) -> ActionPath:
        """将图查询结果转换为ActionPath"""
        from kg_core.schema import Intent
        
        steps = []
        for i, trans in enumerate(path_result.transitions):
            expected_page_id = path_result.pages[i + 1] if i + 1 < len(path_result.pages) else ""
            expected_page = self.graph.get_page(expected_page_id) if expected_page_id else None
            
            step = ActionStep(
                step_index=i + 1,
                action_type=ActionType(trans.get("action_type", "click")),
                target_widget_id=trans.get("trigger_widget_id", ""),
                target_widget_text=trans.get("trigger_widget_text", ""),
                expected_page_id=expected_page_id,
                description=f"{trans.get('action_type', 'click')} {trans.get('trigger_widget_text', '控件')}"
            )
            # 添加额外字段
            step.widget_xpath = trans.get("widget_xpath", "")
            step.expected_page_name = expected_page.page_name if expected_page else ""
            step.confidence = trans.get("confidence", 0.9)
            step.success_rate = trans.get("success_rate", trans.get("success_rate", 0.0))
            
            steps.append(step)
        
        intent_id = Intent.generate_id("", intent)
        path_id = ActionPath.generate_id(intent_id, path_result.pages[0])
        
        return ActionPath(
            path_id=path_id,
            intent_id=intent_id,
            app_id="",
            steps=steps,
            start_page_id=path_result.pages[0],
            end_page_id=path_result.pages[-1]
        )
