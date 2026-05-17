"""
页面抽象器 - 将android_world的State对象转换为KG兼容的页面表示

核心问题:
  UTG的State包含 ui_elements: list[UIElement] (元素级)
  KG的match_current_page()期望 ui_hierarchy: dict (页面级)

本模块负责两个抽象级别之间的转换。
"""

from typing import Optional


def state_to_ui_hierarchy(state) -> dict:
    """将android_world State转换为KG兼容的ui_hierarchy字典。

    提取State.ui_elements中的结构化信息，转为KG PageMatcher所需的格式。

    Args:
        state: android_world State对象，包含pixels、forest、ui_elements

    Returns:
        dict: 包含 "children" 列表的字典，每个child是一个widget描述
    """
    widgets = []
    for elem in (getattr(state, "ui_elements", None) or []):
        w = {
            "class": getattr(elem, "class_name", "") or "",
            "text": getattr(elem, "text", "") or "",
            "content-desc": getattr(elem, "content_description", "") or "",
            "resource-id": (getattr(elem, "resource_id", None)
                            or getattr(elem, "resource_name", None) or ""),
            "clickable": bool(getattr(elem, "is_clickable", False)),
            "scrollable": bool(getattr(elem, "is_scrollable", False)),
            "editable": bool(getattr(elem, "is_editable", False)),
            "enabled": bool(getattr(elem, "is_enabled", True)),
            "visible": bool(getattr(elem, "is_visible", True)),
        }

        # 提取像素级边界框
        bp = getattr(elem, "bbox_pixels", None)
        if bp:
            w["bounds"] = {
                "left": int(bp.x_min),
                "top": int(bp.y_min),
                "right": int(bp.x_max),
                "bottom": int(bp.y_max),
            }

        widgets.append(w)

    return {"children": widgets}


def extract_page_title(state) -> str:
    """从UI元素中启发式提取页面标题。

    搜索策略（优先级从高到低）:
    1. resource_id 包含 'title'、'toolbar_title'、'action_bar_title' 的元素
    2. 类名包含 'Toolbar'、'ActionBar' 的元素的text
    3. 屏幕顶部区域(y < 15%屏幕高度)的第一个非空text

    Args:
        state: android_world State对象

    Returns:
        str: 提取到的页面标题，未找到则返回空字符串
    """
    elems = getattr(state, "ui_elements", None) or []
    pixels = getattr(state, "pixels", None)
    screen_h = pixels.shape[0] if pixels is not None else 2400

    # 策略1: 按resource_id匹配标题控件
    title_keywords = ("title", "toolbar_title", "action_bar_title", "header_text")
    for elem in elems:
        rid = (getattr(elem, "resource_id", None)
               or getattr(elem, "resource_name", None) or "")
        rid_lower = rid.lower()
        text = getattr(elem, "text", None) or ""
        if text and any(kw in rid_lower for kw in title_keywords):
            return text.strip()

    # 策略2: 按类名匹配Toolbar/ActionBar
    toolbar_classes = ("Toolbar", "ActionBar", "CollapsingToolbar")
    for elem in elems:
        cls = getattr(elem, "class_name", "") or ""
        text = getattr(elem, "text", None) or ""
        if text and any(tc in cls for tc in toolbar_classes):
            return text.strip()

    # 策略3: 屏幕顶部区域的第一个非空text
    top_threshold = screen_h * 0.15
    top_elems = []
    for elem in elems:
        bp = getattr(elem, "bbox_pixels", None)
        text = getattr(elem, "text", None) or ""
        if bp and text and bp.y_min < top_threshold:
            top_elems.append((bp.y_min, text.strip()))

    if top_elems:
        top_elems.sort(key=lambda t: t[0])
        return top_elems[0][1]

    return ""


def detect_app_id(state) -> str:
    """从UI元素中提取当前应用的包名。

    遍历所有UI元素的package_name属性，排除系统UI进程，
    返回出现频率最高的包名。

    Args:
        state: android_world State对象

    Returns:
        str: 应用包名，未找到则返回 "unknown"
    """
    elems = getattr(state, "ui_elements", None) or []
    excluded = {
        "com.android.systemui",
        "com.android.launcher",
        "com.android.launcher3",
        "com.google.android.apps.nexuslauncher",
        "com.google.android.inputmethod.latin",
        "",
        None,
    }

    pkg_counts = {}
    for elem in elems:
        pkg = getattr(elem, "package_name", None)
        if pkg not in excluded:
            pkg_counts[pkg] = pkg_counts.get(pkg, 0) + 1

    if not pkg_counts:
        return "unknown"

    # 返回出现次数最多的包名
    return max(pkg_counts, key=pkg_counts.get)


def describe_page(state) -> str:
    """生成当前页面的文本描述，用于KG的语义嵌入。

    从UI元素中提取关键信息，组合成简洁的页面描述文本。

    Args:
        state: android_world State对象

    Returns:
        str: 页面文本描述
    """
    title = extract_page_title(state)
    app_id = detect_app_id(state)
    elems = getattr(state, "ui_elements", None) or []

    # 收集有意义的文本元素
    texts = []
    for elem in elems:
        text = getattr(elem, "text", None) or ""
        desc = getattr(elem, "content_description", None) or ""
        content = text or desc
        if content and len(content) < 50:  # 过滤过长的内容（如正文）
            texts.append(content.strip())

    # 去重并保留前10个
    seen = set()
    unique_texts = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique_texts.append(t)
        if len(unique_texts) >= 10:
            break

    parts = []
    if app_id != "unknown":
        parts.append(f"App: {app_id}")
    if title:
        parts.append(f"Page: {title}")
    if unique_texts:
        parts.append(f"Elements: {', '.join(unique_texts)}")

    return " | ".join(parts) if parts else "Unknown page"
