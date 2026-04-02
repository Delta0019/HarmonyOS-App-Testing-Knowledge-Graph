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
    ENTER = "enter"
    OPEN_APP = "open_app"


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
    structural_fingerprint: str = ""  # 基于 class_name|resource_id 的稳定指纹
    activity: str = ""             # Android Activity 名
    last_visited: str = ""         # ISO 时间戳

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
            "structural_fingerprint": self.structural_fingerprint,
            "activity": self.activity,
            "last_visited": self.last_visited,
            "title": self.title,
            "description": self.description,
            "intents": self.intents,
            "keywords": self.keywords,
            "depth": self.depth,
            "visit_count": self.visit_count,
            "widget_count": len(self.widgets),
            "widgets": [w.to_dict() for w in self.widgets],
        }

    @staticmethod
    def from_dict(d: Dict) -> "Page":
        """从字典反序列化"""
        widgets = []
        for wd in d.get("widgets", []):
            wt = wd.get("widget_type", "other")
            try:
                wt_enum = WidgetType(wt)
            except ValueError:
                wt_enum = WidgetType.OTHER
            widgets.append(Widget(
                widget_id=wd.get("widget_id", ""),
                widget_type=wt_enum,
                text=wd.get("text", ""),
                content_desc=wd.get("content_desc", ""),
                resource_id=wd.get("resource_id", ""),
                xpath=wd.get("xpath", ""),
                bounds=wd.get("bounds", {}),
                is_clickable=wd.get("is_clickable", False),
                is_scrollable=wd.get("is_scrollable", False),
                is_editable=wd.get("is_editable", False),
                semantic_role=wd.get("semantic_role", ""),
            ))
        pt = d.get("page_type", "other")
        try:
            pt_enum = PageType(pt)
        except ValueError:
            pt_enum = PageType.OTHER
        return Page(
            page_id=d["page_id"],
            page_name=d.get("page_name", ""),
            app_id=d.get("app_id", ""),
            page_type=pt_enum,
            state_hash=d.get("state_hash", ""),
            structural_fingerprint=d.get("structural_fingerprint", ""),
            activity=d.get("activity", ""),
            last_visited=d.get("last_visited", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            intents=d.get("intents", []),
            keywords=d.get("keywords", []),
            widgets=widgets,
            depth=d.get("depth", 0),
            visit_count=d.get("visit_count", 0),
        )

    @staticmethod
    def generate_id(app_id: str, page_name: str, state_hash: str = "") -> str:
        """生成页面唯一ID"""
        content = f"{app_id}:{page_name}:{state_hash}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    @staticmethod
    def compute_state_hash(ui_hierarchy: Dict) -> str:
        """计算页面状态哈希"""
        simplified = json.dumps(ui_hierarchy, sort_keys=True)
        return hashlib.md5(simplified.encode()).hexdigest()[:8]

    @staticmethod
    def compute_structural_fingerprint(
        app_id: str, activity: str, widgets_data: List[Dict]
    ) -> str:
        """基于 class_name|resource_id 生成稳定的结构指纹。

        设计原则（搬自 AppGraph）：
        - 只用 class_name + resource_id 作为结构特征
        - 忽略 text（动态内容）和 bounds（布局微调）
        - 这样同一页面在不同数据下仍会匹配

        Args:
            app_id: 包名
            activity: Activity 名
            widgets_data: 控件字典列表，每个至少含 class/class_name 和 resource_id

        Returns:
            16 字符 hex 指纹
        """
        structural_features = sorted(set(
            f"{w.get('class_name') or w.get('class', '')}|{w.get('resource_id', '')}"
            for w in widgets_data
            if w.get("resource_id")
        ))
        if not structural_features:
            structural_features = sorted(set(
                w.get("class_name") or w.get("class", "")
                for w in widgets_data
                if w.get("class_name") or w.get("class")
            ))
        fingerprint = f"{app_id}:{activity}:{','.join(structural_features)}"
        return hashlib.md5(fingerprint.encode("utf-8")).hexdigest()[:16]


@dataclass
class Transition:
    """页面转换关系 (核心边)"""
    transition_id: str
    source_page_id: str            # 源页面
    target_page_id: str            # 目标页面
    
    # 触发信息
    trigger_widget_id: str = ""    # 触发控件
    trigger_widget_text: str = ""  # 触发控件文本
    trigger_widget_class: str = "" # 触发控件类名
    trigger_widget_resource_id: str = ""  # 触发控件 resource_id
    trigger_widget_center: tuple = ()     # 触发控件中心坐标 (x, y)
    action_type: ActionType = ActionType.CLICK

    # 输入数据 (如果需要)
    input_data: Dict[str, str] = field(default_factory=dict)
    input_text: str = ""           # INPUT 类型时的输入文本
    
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
            "trigger_widget_class": self.trigger_widget_class,
            "trigger_widget_resource_id": self.trigger_widget_resource_id,
            "trigger_widget_center": list(self.trigger_widget_center) if self.trigger_widget_center else [],
            "action_type": self.action_type.value,
            "input_data": self.input_data,
            "input_text": self.input_text,
            "success_rate": self.success_rate,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "avg_latency_ms": self.avg_latency_ms,
        }

    @staticmethod
    def from_dict(d: Dict) -> "Transition":
        """从字典反序列化"""
        at = d.get("action_type", "click")
        try:
            at_enum = ActionType(at)
        except ValueError:
            at_enum = ActionType.CLICK
        center = d.get("trigger_widget_center", ())
        if isinstance(center, list):
            center = tuple(center)
        return Transition(
            transition_id=d["transition_id"],
            source_page_id=d.get("source_page_id", ""),
            target_page_id=d.get("target_page_id", ""),
            trigger_widget_id=d.get("trigger_widget_id", ""),
            trigger_widget_text=d.get("trigger_widget_text", ""),
            trigger_widget_class=d.get("trigger_widget_class", ""),
            trigger_widget_resource_id=d.get("trigger_widget_resource_id", ""),
            trigger_widget_center=center,
            action_type=at_enum,
            input_data=d.get("input_data", {}),
            input_text=d.get("input_text", ""),
            success_count=d.get("success_count", 0),
            fail_count=d.get("fail_count", 0),
            avg_latency_ms=d.get("avg_latency_ms", 0),
        )

    @staticmethod
    def generate_id(source_id: str, target_id: str, action: str,
                    widget_key: str = "") -> str:
        """生成转换唯一 ID，加入 widget 标识以区分同页面不同控件的转换"""
        content = f"{source_id}->{target_id}:{action}:{widget_key}"
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
            "action_type": self.action_type.value,  # 符合API规范
            "action": self.action_type.value,  # 保留向后兼容
            "widget_id": self.target_widget_id,
            "widget_text": self.target_widget_text,
            "widget_xpath": getattr(self, 'widget_xpath', ''),  # 添加xpath字段
            "input_text": self.input_text,
            "expected_page": self.expected_page_id,
            "expected_page_name": getattr(self, 'expected_page_name', ''),  # 添加页面名称
            "confidence": getattr(self, 'confidence', 0.0),  # 添加置信度
            "success_rate": getattr(self, 'success_rate', 0.0),  # 添加成功率
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
        """转换为符合API规范的字典格式"""
        # 计算预估耗时（假设每步500ms）
        estimated_time_ms = self.total_steps * 500
        
        return {
            "total_steps": self.total_steps,
            "estimated_time_ms": estimated_time_ms,
            "steps": [s.to_dict() for s in self.steps],
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            # 保留向后兼容的字段
            "path_id": self.path_id,
            "intent_id": self.intent_id,
            "start_page": self.start_page_id,
            "end_page": self.end_page_id
        }
    
    @staticmethod
    def generate_id(intent_id: str, start_page: str) -> str:
        content = f"{intent_id}:{start_page}:{datetime.now().timestamp()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
