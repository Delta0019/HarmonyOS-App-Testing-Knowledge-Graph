"""
动作翻译器 - 将KG页面级ActionStep转换为UTG元素级坐标动作

核心问题:
  KG的ActionStep引用 widget_text="Alarm", widget_id="xxx"
  UTG/Agent需要 click(x=540, y=200) 格式的坐标动作

本模块通过多种匹配策略在当前屏幕上定位KG推荐的widget。
"""

from typing import Optional


def translate_kg_action(kg_step: dict, state) -> Optional[dict]:
    """将KG ActionStep转为屏幕坐标动作。

    匹配策略（按优先级）:
    1. resource_id 精确匹配
    2. text 精确匹配
    3. content_description 精确匹配
    4. text 模糊匹配（包含关系）
    5. widget类型 + 区域启发式匹配

    Args:
        kg_step: KG返回的ActionStep字典，包含:
            - action_type: str ("click", "input", "swipe" 等)
            - widget_id: str (widget标识)
            - widget_text: str (widget显示文本)
            - input_text: str (输入动作的文本内容)
        state: android_world State对象

    Returns:
        dict: 转换后的坐标动作，如 {"action_type": "click", "x": 540, "y": 200}
              匹配失败返回 None
    """
    elems = getattr(state, "ui_elements", None) or []
    if not elems:
        return None

    target_text = kg_step.get("widget_text", "") or ""
    target_rid = kg_step.get("widget_id", "") or ""
    action_type = kg_step.get("action_type", "click")

    matched_elem = None

    # 策略1: resource_id 精确匹配
    if target_rid:
        matched_elem = _match_by_resource_id(elems, target_rid)

    # 策略2: text 精确匹配
    if not matched_elem and target_text:
        matched_elem = _match_by_text_exact(elems, target_text)

    # 策略3: content_description 精确匹配
    if not matched_elem and target_text:
        matched_elem = _match_by_content_desc(elems, target_text)

    # 策略4: text 模糊匹配（包含关系）
    if not matched_elem and target_text:
        matched_elem = _match_by_text_fuzzy(elems, target_text)

    if not matched_elem:
        return None

    return _elem_to_action(matched_elem, action_type, kg_step)


def _match_by_resource_id(elems, target_rid: str):
    """通过resource_id精确匹配。"""
    target_lower = target_rid.lower()
    for elem in elems:
        rid = (getattr(elem, "resource_id", None)
               or getattr(elem, "resource_name", None) or "")
        if rid and rid.lower() == target_lower:
            return elem
    return None


def _match_by_text_exact(elems, target_text: str):
    """通过text精确匹配（不区分大小写）。"""
    target_lower = target_text.lower().strip()
    for elem in elems:
        text = (getattr(elem, "text", None) or "").strip()
        if text and text.lower() == target_lower:
            if _is_interactable(elem):
                return elem
    # 如果没有可交互的精确匹配，返回任意精确匹配
    for elem in elems:
        text = (getattr(elem, "text", None) or "").strip()
        if text and text.lower() == target_lower:
            return elem
    return None


def _match_by_content_desc(elems, target_text: str):
    """通过content_description精确匹配。"""
    target_lower = target_text.lower().strip()
    for elem in elems:
        desc = (getattr(elem, "content_description", None) or "").strip()
        if desc and desc.lower() == target_lower:
            return elem
    return None


def _match_by_text_fuzzy(elems, target_text: str):
    """通过文本包含关系模糊匹配。

    优先匹配可交互元素，然后按文本长度排序（更短的匹配更精确）。
    """
    target_lower = target_text.lower().strip()
    candidates = []

    for elem in elems:
        text = (getattr(elem, "text", None) or "").strip()
        desc = (getattr(elem, "content_description", None) or "").strip()
        content = text or desc
        if not content:
            continue

        content_lower = content.lower()
        if target_lower in content_lower or content_lower in target_lower:
            score = 1.0 if _is_interactable(elem) else 0.5
            # 文本长度越接近目标，匹配越精确
            len_ratio = min(len(target_lower), len(content_lower)) / max(len(target_lower), len(content_lower), 1)
            score += len_ratio * 0.5
            candidates.append((score, elem))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None


def _is_interactable(elem) -> bool:
    """判断元素是否可交互。"""
    return (bool(getattr(elem, "is_clickable", False))
            or bool(getattr(elem, "is_editable", False))
            or bool(getattr(elem, "is_long_clickable", False)))


def _elem_to_action(elem, action_type: str, kg_step: dict) -> dict:
    """将匹配到的UI元素转换为坐标动作。"""
    bp = getattr(elem, "bbox_pixels", None)
    if not bp:
        return None

    cx = int((bp.x_min + bp.x_max) / 2)
    cy = int((bp.y_min + bp.y_max) / 2)

    result = {
        "action_type": action_type,
        "x": cx,
        "y": cy,
        "matched_text": (getattr(elem, "text", None) or ""),
        "matched_rid": (getattr(elem, "resource_id", None) or ""),
    }

    # 输入动作附加文本
    if action_type in ("input", "type") and kg_step.get("input_text"):
        result["text"] = kg_step["input_text"]

    return result
