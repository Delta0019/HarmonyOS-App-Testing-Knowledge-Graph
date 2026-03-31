"""
桥接适配器 - KG宏观路径规划与UTG微观动作执行的核心协调器

BridgeAdapter协调两个系统在Agent step()循环中的交互:
- 任务开始时: 向KG查询宏观路径规划
- 每步执行前: 匹配当前页面，生成合并提示(KG方向 + UTG统计)
- 每步执行后: 双向回馈(更新KG和UTG)，检测偏离并重规划

生命周期:
  1. __init__: 注入KG客户端、UTG图和构建器
  2. plan_task(): 任务开始时查询KG路径
  3. get_combined_hint(): 每步生成合并提示
  4. report_transition(): 每步结束后双向回馈
"""

import os
import logging
from typing import Optional

from android_world.bridge.page_abstractor import (
    state_to_ui_hierarchy,
    extract_page_title,
    detect_app_id,
)
from android_world.bridge.hint_formatter import (
    format_kg_direction,
    format_combined_hint,
)

logger = logging.getLogger(__name__)


class BridgeAdapter:
    """KG与UTG的核心协调器。

    Attributes:
        kg: KGClient实例，提供页面级路径规划
        utg: UTG图实例，提供元素级历史统计
        utg_builder: UTGBuilder实例，用于记录元素级转换
        utg_path: UTG持久化路径
        macro_plan: 当前KG宏观路径规划
        current_step_index: 在宏观路径中的当前位置
        current_page_id: 当前匹配到的KG页面ID
        current_page_name: 当前匹配到的KG页面名称
        current_app_id: 当前应用包名
        current_intent: 当前任务意图
    """

    def __init__(self, kg_client, utg=None, utg_builder=None, utg_path: str = ""):
        self.kg = kg_client
        self.utg = utg
        self.utg_builder = utg_builder
        self.utg_path = utg_path

        # 宏观路径规划状态
        self.macro_plan = None
        self.current_step_index = 0
        self.current_page_id = None
        self.current_page_name = ""
        self.current_app_id = ""
        self.current_intent = ""

        # 统计信息
        self.stats = {
            "kg_queries": 0,
            "kg_page_matches": 0,
            "kg_replans": 0,
            "utg_updates": 0,
            "kg_updates": 0,
        }

    def plan_task(self, app_id: str, intent: str, state) -> dict:
        """任务开始时，向KG查询宏观路径规划。

        Args:
            app_id: 应用包名（可传空字符串，会自动从state检测）
            intent: 任务意图描述
            state: 当前android_world State

        Returns:
            dict: KG query_path()的返回结果
        """
        self.current_app_id = app_id or detect_app_id(state)
        self.current_intent = intent

        # 匹配当前页面
        page_id = self._match_page(state)

        # 查询KG路径
        try:
            result = self.kg.query_path(
                app_id=self.current_app_id,
                intent=intent,
                current_page=page_id,
            )
            self.stats["kg_queries"] += 1

            if result.get("success"):
                self.macro_plan = result.get("path")
                self.current_step_index = 0
                total = self.macro_plan.get("total_steps", 0) if self.macro_plan else 0
                logger.info(f"[KG] 路径规划成功: {total}步, 置信度={result.get('confidence', 0):.2f}")
            else:
                self.macro_plan = None
                logger.info(f"[KG] 未找到路径: {result.get('message', '')}")

            return result

        except Exception as e:
            logger.warning(f"[KG] 路径查询失败: {e}")
            self.macro_plan = None
            return {"success": False, "message": str(e)}

    def get_combined_hint(self, goal: str, state) -> str:
        """生成合并的KG+UTG提示，注入Executor prompt。

        合并两层信息:
        - KG战略方向: 下一个目标页面、建议动作、置信度
        - UTG历史统计: 当前状态下top-k动作的成功率

        Args:
            goal: 任务目标描述
            state: 当前android_world State

        Returns:
            str: 合并后的提示文本，无可用信息时返回空字符串
        """
        # 更新页面匹配
        self._match_page(state)

        # 生成KG战略方向提示
        kg_hint = ""
        if self.macro_plan:
            kg_hint = format_kg_direction(
                self.macro_plan,
                self.current_step_index,
                self.current_page_name,
            )

        # 生成UTG历史统计提示
        utg_hint = ""
        if self.utg:
            try:
                from android_world.utg.retriever import hint
                utg_hint = hint(goal, state, self.utg, topk=5)
            except Exception as e:
                logger.debug(f"[UTG] 提示生成失败: {e}")

        return format_combined_hint(kg_hint, utg_hint)

    def report_transition(self, state_before, action_dict: dict,
                          state_after, outcome: str):
        """双向回馈: 同时更新UTG和KG。

        Args:
            state_before: 动作执行前的State
            action_dict: 执行的动作字典 (从JSONAction.asdict()获得)
            state_after: 动作执行后的State
            outcome: Reflector评估结果 ("A"=成功, "B"=错误页面, "C"=无变化)
        """
        success = (outcome == "A")

        # UTG回馈 (元素级)
        if self.utg_builder:
            try:
                from android_world.utg.state import make_state_id_from_state
                state_before_id = make_state_id_from_state(state_before)
                state_after_id = make_state_id_from_state(state_after)
                transition_success = (state_before_id != state_after_id)

                s1, s2 = self.utg_builder.update(
                    state_before, action_dict, state_after,
                    success=transition_success,
                )
                self.stats["utg_updates"] += 1
                logger.debug(f"[UTG] 更新: {s1[:8]}->>{s2[:8]} (changed={transition_success})")

                # 持久化UTG
                if self.utg_path:
                    self.utg.save(self.utg_path)

            except Exception as e:
                logger.warning(f"[UTG] 更新失败: {e}")

        # KG回馈 (页面级)
        page_before = self._match_page(state_before)
        page_after = self._match_page(state_after)

        if page_before and page_after:
            try:
                self.kg.report_transition(
                    from_page=page_before,
                    action={
                        "type": action_dict.get("action_type", "click"),
                        "widget_text": action_dict.get("text", ""),
                    },
                    to_page=page_after,
                    success=success,
                )
                self.stats["kg_updates"] += 1
            except Exception as e:
                logger.debug(f"[KG] 转换上报失败: {e}")

        # 进度追踪和偏离检测
        if self.macro_plan and page_after:
            expected = self._expected_next_page_id()
            if expected and page_after == expected:
                # 按计划推进
                self.current_step_index += 1
                logger.info(f"[Bridge] 路径推进至步骤 {self.current_step_index}")
            elif page_before != page_after:
                # 页面发生了变化但不是预期页面，尝试重规划
                self._replan(state_after)

    def get_macro_plan_info(self) -> dict:
        """获取当前宏观路径规划信息，用于注入InfoPool。

        Returns:
            dict: 包含路径描述、当前步骤、下一页面、置信度
        """
        if not self.macro_plan:
            return {
                "kg_macro_plan": "",
                "kg_current_step": 0,
                "kg_next_page": "",
                "kg_confidence": 0.0,
            }

        steps = self.macro_plan.get("steps", [])
        total = self.macro_plan.get("total_steps", len(steps))

        # 生成路径描述
        page_names = [s.get("expected_page_name", "?") for s in steps]
        plan_desc = " -> ".join(page_names) if page_names else ""

        next_page = ""
        if self.current_step_index < len(steps):
            next_page = steps[self.current_step_index].get("expected_page_name", "")

        return {
            "kg_macro_plan": f"[{self.current_step_index}/{total}] {plan_desc}",
            "kg_current_step": self.current_step_index,
            "kg_next_page": next_page,
            "kg_confidence": self.macro_plan.get("confidence", 0.0),
        }

    def get_stats(self) -> dict:
        """获取桥接层运行统计。"""
        return dict(self.stats)

    # ---- 内部方法 ----

    def _match_page(self, state) -> Optional[str]:
        """将State匹配到KG中的已知页面。

        Returns:
            str: 匹配到的page_id，未匹配返回None
        """
        try:
            app_id = self.current_app_id or detect_app_id(state)
            ui_hierarchy = state_to_ui_hierarchy(state)
            page_title = extract_page_title(state)

            result = self.kg.match_current_page(
                app_id=app_id,
                ui_hierarchy=ui_hierarchy,
                page_title=page_title,
            )

            if result and result.get("matched"):
                page = result.get("page", {})
                self.current_page_id = page.get("page_id")
                self.current_page_name = page.get("page_name", "")
                self.stats["kg_page_matches"] += 1
                return self.current_page_id

        except Exception as e:
            logger.debug(f"[KG] 页面匹配失败: {e}")

        return None

    def _expected_next_page_id(self) -> Optional[str]:
        """获取宏观路径中下一步期望到达的页面ID。"""
        if not self.macro_plan:
            return None

        steps = self.macro_plan.get("steps", [])
        if self.current_step_index < len(steps):
            return steps[self.current_step_index].get("expected_page")
        return None

    def _replan(self, state):
        """偏离路径时重新规划。

        从当前位置重新查询KG路径。如果KG无法找到路径，
        则降级为仅UTG模式（macro_plan设为None）。
        """
        try:
            page_id = self._match_page(state)
            new_result = self.kg.query_path(
                app_id=self.current_app_id,
                intent=self.current_intent,
                current_page=page_id,
            )
            self.stats["kg_replans"] += 1
            self.stats["kg_queries"] += 1

            if new_result.get("success"):
                self.macro_plan = new_result.get("path")
                self.current_step_index = 0
                total = self.macro_plan.get("total_steps", 0) if self.macro_plan else 0
                logger.info(f"[Bridge] 重规划成功: 新路径{total}步")
            else:
                self.macro_plan = None
                logger.info("[Bridge] 重规划失败，降级为UTG-only模式")

        except Exception as e:
            logger.warning(f"[Bridge] 重规划异常: {e}")
            self.macro_plan = None
