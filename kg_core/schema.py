"""
Schema定义 - 知识图谱的实体和关系结构

实体类型:
- App: 应用
- Page: 页面
- Widget: 控件
- Intent: 意图
- ActionPath: 操作路径

关系类型:
- TRANSITIONS_TO: 页面转换
- CONTAINS_WIDGET: 包含控件
- TRIGGERS: 触发转换
- ACHIEVES_INTENT: 实现意图
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib
import json


class PageType(str, Enum):
    """页面类型枚举"""
    HOME = "home"
    LIST = "list"
    DETAIL = "detail"
    FORM = "form"
    DIALOG = "dialog"
    SEARCH = "search"
    SETTINGS = "settings"
    OTHER = "other"


class WidgetType(str, Enum):
    """控件类型枚举"""
    BUTTON = "button"
    TEXT = "text"
    INPUT = "input"
    IMAGE = "image"
    LIST = "list"
    TAB = "tab"
    ICON = "icon"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    SLIDER = "slider"
    OTHER = "other"


class ActionType(str, Enum):
    """操作类型枚举"""
    CLICK = "click"
    LONG_PRESS = "long_press"
    INPUT = "input"
    SWIPE = "swipe"
    SCROLL = "scroll"
    BACK = "back"
    HOME = "home"


@dataclass
class App:
    """应用实体"""
    app_id: str                    # 唯一标识 (包名)
    app_name: str                  # 应用名称
    version: str = "1.0.0"         # 版本号
    platform: str = "harmonyos"    # 平台
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "app_id": self.app_id,
            "app_name": self.app_name,
            "version": self.version,
            "platform": self.platform,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Widget:
    """控件实体"""
    widget_id: str                 # 唯一标识
    widget_type: WidgetType        # 控件类型
    text: str = ""                 # 文本内容
    content_desc: str = ""         # 内容描述
    resource_id: str = ""          # 资源ID
    xpath: str = ""                # XPath路径
    bounds: Dict[str, int] = field(default_factory=dict)  # 边界框
    
    # 状态属性
    is_clickable: bool = False
    is_scrollable: bool = False
    is_editable: bool = False
    is_enabled: bool = True
    
    # 语义标注
    semantic_role: str = ""        # 语义角色，如"搜索按钮"
    
    def to_dict(self) -> Dict:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "text": self.text,
            "content_desc": self.content_desc,
            "resource_id": self.resource_id,
            "xpath": self.xpath,
            "bounds": self.bounds,
            "is_clickable": self.is_clickable,
            "is_scrollable": self.is_scrollable,
            "is_editable": self.is_editable,
            "semantic_role": self.semantic_role
        }
    
    @staticmethod
    def generate_id(page_id: str, xpath: str) -> str:
        """生成控件唯一ID"""
        content = f"{page_id}:{xpath}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class Page:
    """页面实体 (核心节点)"""
    page_id: str                   # 唯一标识
    page_name: str                 # 页面名称
    app_id: str                    # 所属应用
    page_type: PageType = PageType.OTHER
    
    # 状态特征
    state_hash: str = ""           # 页面状态哈希
    
    # 语义信息
    title: str = ""                # 页面标题
    description: str = ""          # 功能描述 (LLM生成)
    intents: List[str] = field(default_factory=list)  # 可完成的意图
    keywords: List[str] = field(default_factory=list) # 关键词
    
    # 向量嵌入 (存储在向量数据库)
    text_embedding: Optional[List[float]] = None
    
    # 控件列表
    widgets: List[Widget] = field(default_factory=list)
    
    # 截图路径
    screenshot_path: str = ""
    
    # 元数据
    depth: int = 0                 # 从首页的深度
    visit_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "page_id": self.page_id,
            "page_name": self.page_name,
            "app_id": self.app_id,
            "page_type": self.page_type.value,
            "state_hash": self.state_hash,
            "title": self.title,
            "description": self.description,
            "intents": self.intents,
            "keywords": self.keywords,
            "depth": self.depth,
            "visit_count": self.visit_count,
            "widget_count": len(self.widgets)
        }
    
    @staticmethod
    def generate_id(app_id: str, page_name: str, state_hash: str = "") -> str:
        """生成页面唯一ID"""
        content = f"{app_id}:{page_name}:{state_hash}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def compute_state_hash(ui_hierarchy: Dict) -> str:
        """计算页面状态哈希"""
        # 简化版：基于控件树结构计算哈希
        simplified = json.dumps(ui_hierarchy, sort_keys=True)
        return hashlib.md5(simplified.encode()).hexdigest()[:8]


@dataclass
class Transition:
    """页面转换关系 (核心边)"""
    transition_id: str
    source_page_id: str            # 源页面
    target_page_id: str            # 目标页面
    
    # 触发信息
    trigger_widget_id: str = ""    # 触发控件
    trigger_widget_text: str = ""  # 触发控件文本
    action_type: ActionType = ActionType.CLICK
    
    # 输入数据 (如果需要)
    input_data: Dict[str, str] = field(default_factory=dict)
    
    # 统计信息
    success_count: int = 0
    fail_count: int = 0
    avg_latency_ms: int = 0
    
    # 元数据
    discovered_at: datetime = field(default_factory=datetime.now)
    last_verified: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "transition_id": self.transition_id,
            "source_page_id": self.source_page_id,
            "target_page_id": self.target_page_id,
            "trigger_widget_id": self.trigger_widget_id,
            "trigger_widget_text": self.trigger_widget_text,
            "action_type": self.action_type.value,
            "input_data": self.input_data,
            "success_rate": self.success_rate,
            "success_count": self.success_count
        }
    
    @staticmethod
    def generate_id(source_id: str, target_id: str, action: str) -> str:
        content = f"{source_id}->{target_id}:{action}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class ActionStep:
    """单个操作步骤"""
    step_index: int
    action_type: ActionType
    target_widget_id: str
    target_widget_text: str = ""
    input_text: str = ""           # INPUT类型时的输入文本
    expected_page_id: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step_index,
            "action": self.action_type.value,
            "widget_id": self.target_widget_id,
            "widget_text": self.target_widget_text,
            "input_text": self.input_text,
            "expected_page": self.expected_page_id,
            "description": self.description
        }


@dataclass
class Intent:
    """用户意图实体"""
    intent_id: str
    intent_text: str               # 意图描述
    app_id: str
    
    # 语义信息
    keywords: List[str] = field(default_factory=list)
    intent_embedding: Optional[List[float]] = None
    
    # 关联页面
    target_page_id: str = ""       # 目标页面
    
    # 统计
    success_count: int = 0
    avg_steps: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "intent_id": self.intent_id,
            "intent_text": self.intent_text,
            "app_id": self.app_id,
            "keywords": self.keywords,
            "target_page_id": self.target_page_id,
            "success_count": self.success_count,
            "avg_steps": self.avg_steps
        }
    
    @staticmethod
    def generate_id(app_id: str, intent_text: str) -> str:
        content = f"{app_id}:{intent_text}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class ActionPath:
    """操作路径实体"""
    path_id: str
    intent_id: str
    app_id: str
    
    # 路径信息
    steps: List[ActionStep] = field(default_factory=list)
    start_page_id: str = ""
    end_page_id: str = ""
    
    # 质量评估
    confidence: float = 0.0
    is_verified: bool = False
    
    # 执行统计
    execution_count: int = 0
    success_count: int = 0
    avg_time_ms: int = 0
    
    @property
    def total_steps(self) -> int:
        return len(self.steps)
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.execution_count if self.execution_count > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "path_id": self.path_id,
            "intent_id": self.intent_id,
            "total_steps": self.total_steps,
            "steps": [s.to_dict() for s in self.steps],
            "start_page": self.start_page_id,
            "end_page": self.end_page_id,
            "confidence": self.confidence,
            "success_rate": self.success_rate
        }
    
    @staticmethod
    def generate_id(intent_id: str, start_page: str) -> str:
        content = f"{intent_id}:{start_page}:{datetime.now().timestamp()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
