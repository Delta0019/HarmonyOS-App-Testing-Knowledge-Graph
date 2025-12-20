"""
图谱构建器

负责从探索数据构建和更新知识图谱
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from kg_core.schema import (
    App, Page, Widget, Transition, Intent,
    PageType, WidgetType, ActionType
)
from kg_core.graph_store import MemoryGraphStore
from kg_core.vector_store import VectorStoreManager
from kg_core.embeddings import EmbeddingModel


@dataclass
class ExplorationRecord:
    """探索记录"""
    timestamp: datetime
    source_page: Dict
    action: Dict
    target_page: Dict
    success: bool


class GraphBuilder:
    """
    图谱构建器
    
    支持:
    - 从探索数据构建图谱
    - 增量更新
    - 页面去重
    - 意图自动生成
    """
    
    def __init__(
        self,
        graph_store: MemoryGraphStore,
        vector_store: VectorStoreManager,
        embedding_model: EmbeddingModel
    ):
        self.graph = graph_store
        self.vectors = vector_store
        self.embedder = embedding_model
        
        # 页面去重缓存
        self._page_hash_cache: Dict[str, str] = {}  # hash -> page_id
    
    def create_app(self, app_id: str, app_name: str, **kwargs) -> App:
        """创建应用"""
        app = App(
            app_id=app_id,
            app_name=app_name,
            **kwargs
        )
        self.graph.add_app(app)
        return app
    
    def add_page_from_ui(
        self,
        app_id: str,
        ui_hierarchy: Dict,
        screenshot_path: str = None,
        page_name: str = None
    ) -> Page:
        """
        从UI层次结构添加页面
        
        自动处理:
        - 页面去重
        - 控件提取
        - 向量生成
        """
        # 1. 计算状态哈希
        state_hash = Page.compute_state_hash(ui_hierarchy)
        
        # 2. 检查是否已存在
        if state_hash in self._page_hash_cache:
            existing_id = self._page_hash_cache[state_hash]
            existing = self.graph.get_page(existing_id)
            if existing:
                existing.visit_count += 1
                return existing
        
        # 3. 提取页面信息
        if not page_name:
            page_name = self._extract_page_name(ui_hierarchy)
        
        page_id = Page.generate_id(app_id, page_name, state_hash)
        
        # 4. 提取控件
        widgets = self._extract_widgets(ui_hierarchy, page_id)
        
        # 5. 生成描述
        description = self._generate_page_description(ui_hierarchy, widgets)
        
        # 6. 推断页面类型
        page_type = self._infer_page_type(ui_hierarchy, widgets)
        
        # 7. 创建页面
        page = Page(
            page_id=page_id,
            page_name=page_name,
            app_id=app_id,
            page_type=page_type,
            state_hash=state_hash,
            description=description,
            widgets=widgets,
            screenshot_path=screenshot_path or ""
        )
        
        # 8. 添加到图谱
        self.graph.add_page(page)
        self._page_hash_cache[state_hash] = page_id
        
        # 9. 生成并存储向量
        self._store_page_embedding(page)
        
        return page
    
    def add_transition_from_action(
        self,
        source_page: Page,
        target_page: Page,
        action: Dict
    ) -> Transition:
        """
        从操作记录添加转换
        
        Args:
            source_page: 源页面
            target_page: 目标页面
            action: 操作信息 {"type": "click", "widget_id": "...", "widget_text": "..."}
        """
        action_type = ActionType(action.get("type", "click"))
        
        transition = Transition(
            transition_id=Transition.generate_id(
                source_page.page_id,
                target_page.page_id,
                action_type.value
            ),
            source_page_id=source_page.page_id,
            target_page_id=target_page.page_id,
            trigger_widget_id=action.get("widget_id", ""),
            trigger_widget_text=action.get("widget_text", ""),
            action_type=action_type,
            success_count=1
        )
        
        self.graph.add_transition(transition)
        return transition
    
    def process_exploration_record(self, record: ExplorationRecord) -> bool:
        """
        处理单条探索记录
        
        用于实时图谱更新
        """
        # 1. 添加/获取源页面
        source_page = self.add_page_from_ui(
            app_id=record.source_page.get("app_id", ""),
            ui_hierarchy=record.source_page.get("ui_hierarchy", {}),
            page_name=record.source_page.get("page_name")
        )
        
        # 2. 添加/获取目标页面
        target_page = self.add_page_from_ui(
            app_id=record.target_page.get("app_id", ""),
            ui_hierarchy=record.target_page.get("ui_hierarchy", {}),
            page_name=record.target_page.get("page_name")
        )
        
        # 3. 添加转换
        self.add_transition_from_action(source_page, target_page, record.action)
        
        return True
    
    def build_from_exploration_log(
        self,
        log_path: str,
        progress_callback: Callable[[int, int], None] = None
    ):
        """
        从探索日志批量构建图谱
        
        Args:
            log_path: 探索日志路径
            progress_callback: 进度回调
        """
        # 实际实现中从文件读取
        pass
    
    def auto_generate_intents(self, app_id: str):
        """
        自动生成意图
        
        基于页面描述和功能自动生成用户意图
        """
        pages = self.graph.get_all_pages(app_id)
        
        for page in pages:
            if page.intents:
                for intent_text in page.intents:
                    intent_id = Intent.generate_id(app_id, intent_text)
                    vec = self.embedder.encode_single(intent_text)
                    self.vectors.intents.insert(intent_id, vec, {
                        "text": intent_text,
                        "app_id": app_id,
                        "target_page_id": page.page_id
                    })
    
    # ==================== 辅助方法 ====================
    
    def _extract_page_name(self, ui_hierarchy: Dict) -> str:
        """从UI层次结构提取页面名称"""
        # 尝试从标题栏提取
        def find_title(node):
            if isinstance(node, dict):
                # 检查是否是标题控件
                if node.get("class", "").endswith("Title") or \
                   node.get("resource-id", "").endswith("title"):
                    return node.get("text", "")
                
                # 递归搜索
                for child in node.get("children", []):
                    title = find_title(child)
                    if title:
                        return title
            return ""
        
        title = find_title(ui_hierarchy)
        return title if title else f"page_{datetime.now().strftime('%H%M%S')}"
    
    def _extract_widgets(self, ui_hierarchy: Dict, page_id: str) -> List[Widget]:
        """从UI层次结构提取可交互控件"""
        widgets = []
        
        def traverse(node, xpath=""):
            if not isinstance(node, dict):
                return
            
            current_xpath = f"{xpath}/{node.get('class', 'unknown')}"
            
            # 判断是否可交互
            is_interactive = (
                node.get("clickable", False) or
                node.get("scrollable", False) or
                node.get("editable", False)
            )
            
            if is_interactive:
                widget_id = Widget.generate_id(page_id, current_xpath)
                widget = Widget(
                    widget_id=widget_id,
                    widget_type=self._infer_widget_type(node),
                    text=node.get("text", ""),
                    content_desc=node.get("content-desc", ""),
                    resource_id=node.get("resource-id", ""),
                    xpath=current_xpath,
                    bounds=node.get("bounds", {}),
                    is_clickable=node.get("clickable", False),
                    is_scrollable=node.get("scrollable", False),
                    is_editable=node.get("editable", False)
                )
                widgets.append(widget)
            
            # 递归处理子节点
            for i, child in enumerate(node.get("children", [])):
                traverse(child, f"{current_xpath}[{i}]")
        
        traverse(ui_hierarchy)
        return widgets
    
    def _infer_widget_type(self, node: Dict) -> WidgetType:
        """推断控件类型"""
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
    
    def _infer_page_type(self, ui_hierarchy: Dict, widgets: List[Widget]) -> PageType:
        """推断页面类型"""
        # 基于控件组成推断
        widget_types = [w.widget_type for w in widgets]
        
        # 有大量输入框 -> 表单
        if widget_types.count(WidgetType.INPUT) >= 2:
            return PageType.FORM
        
        # 有列表控件 -> 列表页
        if WidgetType.LIST in widget_types:
            return PageType.LIST
        
        # 默认
        return PageType.OTHER
    
    def _generate_page_description(self, ui_hierarchy: Dict, widgets: List[Widget]) -> str:
        """生成页面描述"""
        # 收集所有文本
        texts = []
        
        def collect_text(node):
            if isinstance(node, dict):
                text = node.get("text", "").strip()
                if text and len(text) < 50:  # 过滤过长文本
                    texts.append(text)
                for child in node.get("children", []):
                    collect_text(child)
        
        collect_text(ui_hierarchy)
        
        # 组合描述
        if texts:
            return f"包含: {', '.join(texts[:5])}"
        return ""
    
    def _store_page_embedding(self, page: Page):
        """存储页面嵌入向量"""
        # 组合文本
        text_parts = [page.page_name]
        if page.description:
            text_parts.append(page.description)
        if page.intents:
            text_parts.extend(page.intents)
        
        combined_text = " ".join(text_parts)
        vec = self.embedder.encode_single(combined_text)
        
        self.vectors.pages.insert(page.page_id, vec, {
            "name": page.page_name,
            "description": page.description,
            "intents": page.intents
        })
