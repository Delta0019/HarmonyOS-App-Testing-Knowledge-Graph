# utg/state.py
import hashlib
from typing import Any, Iterable

def _q(x: float, q: float = 0.02) -> float:
    # 量化到 2% 屏幕精度，防止微小抖动造成状态爆炸
    return round(x / q) * q

def _bool01(v: Any) -> int:
    return 1 if bool(v) else 0

def skeletonize_from_state(state, *, q: float = 0.02) -> str:
    """
    state: android_world_v3.android_world.env.interface.State
      - state.pixels: np.ndarray (H, W, 3)
      - state.ui_elements: list[UIElement]
    """
    h, w = state.pixels.shape[0], state.pixels.shape[1]
    elems = getattr(state, "ui_elements", None) or []

    feats = []
    for e in elems:
        cls = getattr(e, "class_name", "") or ""
        rid = (
            getattr(e, "resource_id", None)
            or getattr(e, "resource_name", None)
            or ""
        )

        clickable = _bool01(getattr(e, "is_clickable", None))
        editable = _bool01(getattr(e, "is_editable", None))
        scrollable = _bool01(getattr(e, "is_scrollable", None))
        enabled = _bool01(getattr(e, "is_enabled", None))
        visible = _bool01(getattr(e, "is_visible", None))

        bp = getattr(e, "bbox_pixels", None)
        if bp is not None:
            x1 = _q(bp.x_min / w, q)
            y1 = _q(bp.y_min / h, q)
            x2 = _q(bp.x_max / w, q)
            y2 = _q(bp.y_max / h, q)
            b = f"{x1:.2f},{y1:.2f},{x2:.2f},{y2:.2f}"
            sort_key = (y1, x1, y2, x2)
        else:
            b = "na"
            sort_key = (0.0, 0.0, 0.0, 0.0)

        # 不直接用 text，避免动态内容导致状态爆炸
        # 如果你很想用：可以加 text_len_bucket
        feats.append((sort_key, cls, rid, clickable, editable, scrollable, enabled, visible, b))

    feats.sort(key=lambda t: t[0])

    lines = []
    for (_, cls, rid, c, ed, sc, en, vis, b) in feats:
        lines.append(f"{cls}|{rid}|c{c}|ed{ed}|sc{sc}|en{en}|v{vis}|b{b}")

    return "\n".join(lines)

def make_state_id_from_state(state, *, q: float = 0.02) -> str:
    s = skeletonize_from_state(state, q=q)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
