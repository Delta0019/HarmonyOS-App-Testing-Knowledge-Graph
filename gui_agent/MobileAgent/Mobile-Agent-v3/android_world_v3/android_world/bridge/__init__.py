"""
桥接层模块 - 协调知识图谱(KG)宏观路径规划与UTG微观动作执行

本模块提供:
- BridgeAdapter: KG与UTG的核心协调器
- page_abstractor: 将android_world State转为KG页面格式
- action_translator: 将KG ActionStep转为屏幕坐标
- hint_formatter: 合并KG+UTG提示
"""

from android_world.bridge.adapter import BridgeAdapter
from android_world.bridge.page_abstractor import (
    state_to_ui_hierarchy,
    extract_page_title,
    detect_app_id,
)
from android_world.bridge.action_translator import translate_kg_action
from android_world.bridge.hint_formatter import format_kg_direction, format_combined_hint

__all__ = [
    "BridgeAdapter",
    "state_to_ui_hierarchy",
    "extract_page_title",
    "detect_app_id",
    "translate_kg_action",
    "format_kg_direction",
    "format_combined_hint",
]
