"""
RAG引擎模块

检索增强生成引擎，用于:
- 组合向量检索和图结构检索
- 构建上下文供LLM使用
- 生成操作指导
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

from kg_core.graph_store import BaseGraphStore
from kg_core.vector_store import VectorStoreManager
from kg_core.embeddings import EmbeddingModel
from .path_finder import PathFinder, QueryResult
from .page_matcher import PageMatcher, MatchResult


@dataclass
class RAGContext:
    """RAG上下文"""
    query: str
    retrieved_paths: List[Dict]
    retrieved_pages: List[Dict]
    graph_context: str
    suggested_actions: List[Dict]
    confidence: float
    
    def to_prompt(self) -> str:
        """转换为LLM提示词格式"""
        prompt_parts = [
            f"用户意图: {self.query}",
            "",
            "相关页面信息:",
        ]
        
        for page in self.retrieved_pages[:3]:
            prompt_parts.append(f"- {page['name']}: {page.get('description', '')}")
        
        if self.retrieved_paths:
            prompt_parts.append("")
            prompt_parts.append("推荐操作路径:")
            for i, path in enumerate(self.retrieved_paths[:2], 1):
                steps_desc = " → ".join([
                    s.get('description', s.get('widget_text', ''))
                    for s in path.get('steps', [])
                ])
                prompt_parts.append(f"{i}. {steps_desc}")
        
        if self.suggested_actions:
            prompt_parts.append("")
            prompt_parts.append("下一步建议操作:")
            for action in self.suggested_actions[:3]:
                prompt_parts.append(
                    f"- {action['action']}: {action.get('widget_text', '')} "
                    f"→ {action.get('leads_to', '')}"
                )
        
        return "\n".join(prompt_parts)
    
    def to_dict(self) -> Dict:
        """转换为符合API规范的字典格式"""
        return {
            "prompt": self.to_prompt(),
            "context": {
                "relevant_pages": [
                    {
                        "page_id": p.get("id", ""),
                        "page_name": p.get("name", ""),
                        "description": p.get("description", ""),
                        "relevance_score": p.get("similarity", 0.0)
                    }
                    for p in self.retrieved_pages
                ],
                "recommended_paths": [
                    {
                        "path_id": p.get("path_id", ""),
                        "steps": p.get("steps", []),
                        "confidence": p.get("confidence", 0.0),
                        "success_rate": p.get("success_rate", 0.0)
                    }
                    for p in self.retrieved_paths
                ],
                "historical_cases": {
                    "successful": [],
                    "failed": []
                },
                "tips": []
            },
            "suggested_actions": self.suggested_actions
        }


class RAGEngine:
    """
    RAG引擎
    
    融合向量检索和图结构检索，为Agent提供决策支持
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
        
        # 组合查询组件
        self.path_finder = PathFinder(graph_store, vector_store, embedding_model)
        self.page_matcher = PageMatcher(graph_store, vector_store, embedding_model)
    
    def retrieve(
        self,
        app_id: str,
        query: str,
        current_page_id: str = None,
        include_paths: bool = True,
        include_pages: bool = True,
        top_k: int = 5
    ) -> RAGContext:
        """
        执行RAG检索
        
        双通道检索:
        1. 向量检索: 基于语义相似度
        2. 图结构检索: 基于路径关系
        """
        # 1. 编码查询
        query_vec = self.embedder.encode_single(query)
        
        retrieved_paths = []
        retrieved_pages = []
        suggested_actions = []
        confidence = 0.0
        
        # 2. 向量检索相关页面
        if include_pages:
            page_results = self.vectors.pages.search(query_vec, top_k=top_k)
            for r in page_results:
                page = self.graph.get_page(r.id)
                if page:
                    retrieved_pages.append({
                        "id": page.page_id,
                        "name": page.page_name,
                        "description": page.description,
                        "intents": page.intents,
                        "similarity": r.score
                    })
        
        # 3. 图结构检索路径
        if include_paths and current_page_id:
            path_result = self.path_finder.find_path_by_intent(
                app_id=app_id,
                intent=query,
                current_page_id=current_page_id
            )
            
            if path_result.success:
                retrieved_paths.append(path_result.path.to_dict())
                confidence = path_result.confidence
                
                # 获取下一步建议
                if path_result.path.steps:
                    first_step = path_result.path.steps[0]
                    suggested_actions.append({
                        "action": first_step.action_type.value,
                        "widget_id": first_step.target_widget_id,
                        "widget_text": first_step.target_widget_text,
                        "leads_to": first_step.expected_page_id,
                        "confidence": confidence
                    })
                
                # 添加备选路径
                for alt in (path_result.alternatives or []):
                    retrieved_paths.append(alt.to_dict())
        
        # 4. 补充当前页面的可用操作
        if current_page_id:
            transitions = self.graph.get_outgoing_transitions(current_page_id)
            for t in transitions[:5]:
                target = self.graph.get_page(t.target_page_id)
                suggested_actions.append({
                    "action": t.action_type.value,
                    "widget_id": t.trigger_widget_id,
                    "widget_text": t.trigger_widget_text,
                    "leads_to": target.page_name if target else "",
                    "confidence": t.success_rate
                })
        
        # 5. 构建图上下文描述
        graph_context = self._build_graph_context(
            current_page_id, 
            retrieved_pages, 
            retrieved_paths
        )
        
        return RAGContext(
            query=query,
            retrieved_paths=retrieved_paths,
            retrieved_pages=retrieved_pages,
            graph_context=graph_context,
            suggested_actions=suggested_actions,
            confidence=confidence
        )
    
    def _build_graph_context(
        self,
        current_page_id: str,
        pages: List[Dict],
        paths: List[Dict]
    ) -> str:
        """构建图结构上下文描述"""
        parts = []
        
        if current_page_id:
            current_page = self.graph.get_page(current_page_id)
            if current_page:
                parts.append(f"当前位置: {current_page.page_name}")
                
                # 可达页面
                reachable = self.graph.get_reachable_pages(current_page_id, max_depth=2)
                reachable_names = []
                for pid in reachable[:5]:
                    p = self.graph.get_page(pid)
                    if p and p.page_id != current_page_id:
                        reachable_names.append(p.page_name)
                if reachable_names:
                    parts.append(f"可达页面: {', '.join(reachable_names)}")
        
        if paths:
            parts.append(f"找到 {len(paths)} 条相关路径")
        
        if pages:
            top_pages = [p['name'] for p in pages[:3]]
            parts.append(f"相关页面: {', '.join(top_pages)}")
        
        return "; ".join(parts)
    
    def generate_action_guidance(
        self,
        app_id: str,
        intent: str,
        current_page_id: str,
        current_ui: Dict = None
    ) -> Dict:
        """
        生成操作指导
        
        返回适合直接传给Agent的操作指令
        """
        # 1. 匹配当前页面
        if current_ui:
            match_result = self.page_matcher.match_page(
                app_id=app_id,
                ui_hierarchy=current_ui
            )
            if match_result:
                current_page_id = match_result.page_id
        
        # 2. RAG检索
        context = self.retrieve(
            app_id=app_id,
            query=intent,
            current_page_id=current_page_id
        )
        
        # 3. 构建指导
        guidance = {
            "intent": intent,
            "current_page": current_page_id,
            "confidence": context.confidence,
            "next_action": None,
            "full_path": None,
            "context": context.to_prompt()
        }
        
        if context.suggested_actions:
            best_action = max(
                context.suggested_actions,
                key=lambda x: x.get("confidence", 0)
            )
            guidance["next_action"] = best_action
        
        if context.retrieved_paths:
            guidance["full_path"] = context.retrieved_paths[0]
        
        return guidance
    
    def query(
        self,
        app_id: str,
        question: str,
        current_page_id: str = None
    ) -> str:
        """
        简单问答接口
        
        返回自然语言回答
        """
        context = self.retrieve(
            app_id=app_id,
            query=question,
            current_page_id=current_page_id
        )
        
        # 构建回答
        if context.retrieved_paths:
            path = context.retrieved_paths[0]
            steps = path.get('steps', [])
            if steps:
                step_descs = [s.get('description', '') for s in steps]
                return f"要完成'{question}'，请按以下步骤操作：\n" + \
                       "\n".join(f"{i+1}. {d}" for i, d in enumerate(step_descs))
        
        if context.retrieved_pages:
            pages = [p['name'] for p in context.retrieved_pages[:3]]
            return f"与'{question}'相关的页面有：{', '.join(pages)}"
        
        return f"抱歉，未找到与'{question}'相关的信息"
