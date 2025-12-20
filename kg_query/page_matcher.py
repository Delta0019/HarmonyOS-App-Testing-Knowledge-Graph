"""
页面匹配模块

根据当前页面状态匹配图谱中的页面节点
支持:
- 基于UI结构的匹配
- 基于截图的视觉匹配
- 混合匹配策略
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from kg_core.schema import Page, Widget, WidgetType
from kg_core.graph_store import BaseGraphStore
from kg_core.vector_store import VectorStoreManager
from kg_core.embeddings import EmbeddingModel


@dataclass
class MatchResult:
    """页面匹配结果"""
    page_id: str
    page_name: str
    confidence: float
    match_type: str  # structural | visual | hybrid
    available_actions: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            "page_id": self.page_id,
            "page_name": self.page_name,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "available_actions": self.available_actions
        }


class PageMatcher:
    """
    页面匹配器
    
    将当前屏幕状态匹配到图谱中已知的页面
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
    
    def match_page(
        self,
        app_id: str,
        ui_hierarchy: Dict = None,
        screenshot_embedding: List[float] = None,
        page_title: str = None,
        strategy: str = "hybrid"
    ) -> Optional[MatchResult]:
        """
        匹配当前页面
        
        Args:
            app_id: 应用ID
            ui_hierarchy: UI控件树
            screenshot_embedding: 截图向量
            page_title: 页面标题
            strategy: 匹配策略 (structural | visual | hybrid)
        """
        candidates = []
        
        # 策略1: 基于结构的匹配
        if strategy in ["structural", "hybrid"] and ui_hierarchy:
            struct_matches = self._match_by_structure(app_id, ui_hierarchy)
            candidates.extend(struct_matches)
        
        # 策略2: 基于标题的精确匹配
        if page_title:
            page = self.graph.find_page_by_name(page_title, app_id)
            if page:
                candidates.append((page.page_id, 1.0, "title"))
        
        # 策略3: 基于向量的语义匹配
        if strategy in ["visual", "hybrid"]:
            if screenshot_embedding:
                vec_matches = self._match_by_vector(screenshot_embedding)
                candidates.extend(vec_matches)
            elif ui_hierarchy:
                # 将UI结构转为文本描述进行匹配
                ui_text = self._hierarchy_to_text(ui_hierarchy)
                text_vec = self.embedder.encode_single(ui_text)
                vec_matches = self._match_by_vector(text_vec)
                candidates.extend(vec_matches)
        
        if not candidates:
            return None
        
        # 合并和排序候选结果
        merged = self._merge_candidates(candidates)
        if not merged:
            return None
        
        best_match = merged[0]
        page_id, confidence, match_type = best_match
        
        # 获取页面详情
        page = self.graph.get_page(page_id)
        if not page:
            return None
        
        # 获取可用操作
        available_actions = self._get_available_actions(page_id)
        
        return MatchResult(
            page_id=page_id,
            page_name=page.page_name,
            confidence=confidence,
            match_type=match_type,
            available_actions=available_actions
        )
    
    def _match_by_structure(
        self, 
        app_id: str, 
        ui_hierarchy: Dict
    ) -> List[Tuple[str, float, str]]:
        """基于UI结构匹配"""
        # 计算当前页面的结构签名
        current_signature = self._compute_structure_signature(ui_hierarchy)
        
        # 与图谱中的页面对比
        matches = []
        pages = self.graph.get_all_pages(app_id)
        
        for page in pages:
            if page.state_hash == current_signature:
                matches.append((page.page_id, 1.0, "structural"))
            else:
                # 计算结构相似度
                similarity = self._compute_structural_similarity(
                    ui_hierarchy, page
                )
                if similarity > 0.7:
                    matches.append((page.page_id, similarity, "structural"))
        
        return matches
    
    def _match_by_vector(
        self, 
        query_vector: List[float]
    ) -> List[Tuple[str, float, str]]:
        """基于向量匹配"""
        results = self.vectors.pages.search(query_vector, top_k=5)
        return [
            (r.id, r.score, "visual") 
            for r in results 
            if r.score > 0.6
        ]
    
    def _compute_structure_signature(self, ui_hierarchy: Dict) -> str:
        """计算UI结构签名"""
        return Page.compute_state_hash(ui_hierarchy)
    
    def _compute_structural_similarity(
        self, 
        ui_hierarchy: Dict, 
        page: Page
    ) -> float:
        """计算结构相似度"""
        # 简化实现：基于控件类型和数量
        current_widgets = self._extract_widgets_from_hierarchy(ui_hierarchy)
        page_widgets = page.widgets
        
        if not current_widgets or not page_widgets:
            return 0.0
        
        # 计算控件类型分布的相似度
        current_types = set(w.get("type", "") for w in current_widgets)
        page_types = set(w.widget_type.value for w in page_widgets)
        
        intersection = len(current_types & page_types)
        union = len(current_types | page_types)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_widgets_from_hierarchy(self, hierarchy: Dict) -> List[Dict]:
        """从UI层次结构中提取控件"""
        widgets = []
        
        def traverse(node):
            if isinstance(node, dict):
                widget_info = {
                    "type": node.get("type", node.get("class", "")),
                    "text": node.get("text", ""),
                    "clickable": node.get("clickable", False)
                }
                if widget_info["type"]:
                    widgets.append(widget_info)
                
                # 遍历子节点
                children = node.get("children", [])
                for child in children:
                    traverse(child)
        
        traverse(hierarchy)
        return widgets
    
    def _hierarchy_to_text(self, hierarchy: Dict) -> str:
        """将UI层次结构转为文本描述"""
        widgets = self._extract_widgets_from_hierarchy(hierarchy)
        texts = []
        for w in widgets:
            if w.get("text"):
                texts.append(w["text"])
        return " ".join(texts)
    
    def _merge_candidates(
        self, 
        candidates: List[Tuple[str, float, str]]
    ) -> List[Tuple[str, float, str]]:
        """合并候选结果"""
        # 按page_id聚合
        merged = {}
        for page_id, score, match_type in candidates:
            if page_id not in merged:
                merged[page_id] = {"scores": [], "types": []}
            merged[page_id]["scores"].append(score)
            merged[page_id]["types"].append(match_type)
        
        # 计算综合得分
        results = []
        for page_id, data in merged.items():
            avg_score = sum(data["scores"]) / len(data["scores"])
            # 混合匹配加分
            if len(set(data["types"])) > 1:
                avg_score = min(avg_score * 1.1, 1.0)
            primary_type = max(set(data["types"]), key=data["types"].count)
            results.append((page_id, avg_score, primary_type))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def _get_available_actions(self, page_id: str) -> List[Dict]:
        """获取页面的可用操作"""
        transitions = self.graph.get_outgoing_transitions(page_id)
        actions = []
        
        for t in transitions:
            target_page = self.graph.get_page(t.target_page_id)
            actions.append({
                "widget_id": t.trigger_widget_id,
                "widget_text": t.trigger_widget_text,
                "action": t.action_type.value,
                "leads_to": target_page.page_name if target_page else t.target_page_id,
                "success_rate": t.success_rate
            })
        
        return actions
    
    def find_similar_pages(
        self, 
        page_description: str, 
        top_k: int = 5
    ) -> List[MatchResult]:
        """根据描述查找相似页面"""
        desc_vec = self.embedder.encode_single(page_description)
        results = self.vectors.pages.search(desc_vec, top_k=top_k)
        
        matches = []
        for r in results:
            page = self.graph.get_page(r.id)
            if page:
                matches.append(MatchResult(
                    page_id=page.page_id,
                    page_name=page.page_name,
                    confidence=r.score,
                    match_type="semantic",
                    available_actions=self._get_available_actions(page.page_id)
                ))
        
        return matches
