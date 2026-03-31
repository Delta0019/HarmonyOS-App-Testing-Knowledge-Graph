"""
提示格式化器 - 将KG战略方向和UTG历史统计合并为LLM可读的提示文本

生成注入到Executor prompt中的导航提示，包含:
- KG宏观路径进度和下一步方向
- UTG元素级历史成功率统计
"""


def format_kg_direction(macro_plan: dict, current_step: int, matched_page_name: str = "") -> str:
    """格式化KG的战略方向提示。

    Args:
        macro_plan: KG query_path()返回的path字典，包含total_steps和steps列表
        current_step: 当前在路径中的步骤索引(0-based)
        matched_page_name: 当前匹配到的KG页面名称

    Returns:
        str: 格式化的方向提示文本，无路径时返回空字符串
    """
    if not macro_plan or "steps" not in macro_plan:
        return ""

    steps = macro_plan.get("steps", [])
    total = macro_plan.get("total_steps", len(steps))

    if current_step >= total or not steps:
        return "Navigation plan completed. Verify if the task goal is achieved."

    step = steps[current_step]
    lines = [
        f"[Knowledge Graph Navigation] Progress: step {current_step + 1}/{total}",
    ]

    if matched_page_name:
        lines.append(f"  Current page: {matched_page_name}")

    expected_page = step.get("expected_page_name") or step.get("expected_page", "")
    if expected_page:
        lines.append(f"  Next target page: {expected_page}")

    action_type = step.get("action_type", "")
    widget_text = step.get("widget_text", "")
    if action_type and widget_text:
        lines.append(f"  Suggested action: {action_type} '{widget_text}'")

    confidence = step.get("confidence", 0)
    if confidence > 0:
        lines.append(f"  Confidence: {confidence:.0%}")

    # 展示后续1-2步作为预览
    remaining = steps[current_step + 1: current_step + 3]
    if remaining:
        preview = " -> ".join(
            s.get("expected_page_name", s.get("expected_page", "?"))
            for s in remaining
        )
        lines.append(f"  Upcoming: {preview}")

    return "\n".join(lines)


def format_combined_hint(kg_hint: str, utg_hint: str) -> str:
    """合并KG方向提示和UTG历史统计为最终注入prompt的文本。

    Args:
        kg_hint: format_kg_direction()的输出
        utg_hint: UTG retriever.hint()的输出

    Returns:
        str: 合并后的提示文本，两者都为空时返回空字符串
    """
    parts = []

    if kg_hint:
        parts.append(kg_hint)

    if utg_hint and "No historical actions" not in utg_hint:
        parts.append(utg_hint)

    if not parts:
        return ""

    return "\n\n".join(parts)
