# utg/retriever.py
from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    from .graph import UTG

from .state import make_state_id_from_state


def hint(goal: str, state, utg: "UTG", topk: int = 5) -> str:
    """
    Generate action hints based on historical UTG data.
    
    Args:
        goal: The current task goal/instruction
        state: Current android_world State object
        utg: The UI Transition Graph
        topk: Number of top actions to suggest
        
    Returns:
        A formatted string with top-k action suggestions
    """
    state_id = make_state_id_from_state(state)
    
    # Get all outgoing edges from current state
    out_edges = utg.out_edges(state_id)
    
    if not out_edges:
        return "No historical actions available for this state."
    
    # Sort by success rate (descending), then by count (descending)
    sorted_edges = sorted(
        out_edges,
        key=lambda x: (x[3].success_rate, x[3].count),
        reverse=True
    )
    
    # Take top-k
    top_edges = sorted_edges[:topk]
    
    # Format output
    lines = [f"[UTG Hints] Top {len(top_edges)} actions for current state:\n"]
    
    for idx, (s1, action_dict, s2, stat) in enumerate(top_edges, 1):
        success_rate = stat.success_rate
        action_type = action_dict.get("action", "unknown")
        
        # Format action details based on type
        action_desc = _format_action(action_dict)
        
        lines.append(
            f"{idx}. {action_desc}\n"
            f"   Success: {stat.success}/{stat.count} ({success_rate:.1%}) | "
            f"Fail: {stat.fail}"
        )
    
    return "\n".join(lines)


def _format_action(action_dict: dict) -> str:
    """Format action dictionary into human-readable string."""
    action_type = action_dict.get("action", "unknown")
    
    if action_type == "click":
        coord = action_dict.get("coordinate", [])
        if coord:
            return f"Click at ({coord[0]}, {coord[1]})"
        return "Click"
    
    elif action_type == "type":
        text = action_dict.get("text", "")
        text_preview = text[:30] + "..." if len(text) > 30 else text
        return f"Type: \"{text_preview}\""
    
    elif action_type == "swipe":
        coord1 = action_dict.get("coordinate", [])
        coord2 = action_dict.get("coordinate2", [])
        if coord1 and coord2:
            return f"Swipe from ({coord1[0]}, {coord1[1]}) to ({coord2[0]}, {coord2[1]})"
        return "Swipe"
    
    elif action_type == "long_press":
        coord = action_dict.get("coordinate", [])
        if coord:
            return f"Long press at ({coord[0]}, {coord[1]})"
        return "Long press"
    
    elif action_type == "open_app":
        app_name = action_dict.get("text", action_dict.get("app_name", ""))
        return f"Open app: {app_name}"
    
    elif action_type == "system_button":
        button = action_dict.get("button", "")
        return f"Press {button} button"
    
    elif action_type == "answer":
        text = action_dict.get("text", "")
        text_preview = text[:30] + "..." if len(text) > 30 else text
        return f"Answer: \"{text_preview}\""
    
    elif action_type in ["done", "terminate"]:
        return "Task complete"
    
    else:
        # Generic fallback
        try:
            action_str = json.dumps(action_dict, ensure_ascii=False)
            if len(action_str) > 50:
                action_str = action_str[:50] + "..."
            return f"Action: {action_str}"
        except:
            return f"Action type: {action_type}"
