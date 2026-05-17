"""
知识图谱预建脚本 - 从AndroidWorld应用中自动构建KG

两种预建方式:
1. 静态注册: 从task_metadata.json和app信息中提取意图和应用映射
2. 动态探索: 连接模拟器，对每个app执行随机操作，收集页面和转换

使用方式:
    # 仅静态注册（不需要模拟器）
    python -m android_world.bridge.kg_bootstrap --mode static --output kg_data/

    # 动态探索（需要模拟器运行）
    python -m android_world.bridge.kg_bootstrap --mode explore --output kg_data/ --steps 30
"""

import json
import os
import sys
import hashlib
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# AndroidWorld 应用包名映射（app显示名 -> 包名）
APP_PACKAGE_MAP = {
    "audio recorder": "com.dimowner.audiorecorder",
    "broccoli": "com.flauschcode.broccoli",
    "camera": "com.android.camera2",
    "chrome": "com.android.chrome",
    "clock": "com.google.android.deskclock",
    "contacts": "com.google.android.contacts",
    "files": "com.google.android.documentsui",
    "joplin": "net.cozic.joplin",
    "markor": "net.gsantner.markor",
    "messages": "com.google.android.apps.messaging",
    "osmand": "net.osmand",
    "opentracks": "de.dennisguse.opentracks",
    "pro expense": "com.arduia.expense",
    "retro music": "code.name.monkey.retromusic",
    "settings": "com.android.settings",
    "simple calendar pro": "com.simplemobiletools.calendar.pro",
    "simple draw pro": "com.simplemobiletools.draw.pro",
    "simple gallery pro": "com.simplemobiletools.gallery.pro",
    "simple sms messenger": "com.simplemobiletools.smsmessenger",
    "tasks": "org.tasks",
    "vlc": "org.videolan.vlc",
}

# 任务名称前缀 -> 应用名称的映射
TASK_PREFIX_TO_APP = {
    "AudioRecorder": "audio recorder",
    "Broccoli": "broccoli",
    "Browser": "chrome",
    "Camera": "camera",
    "Clock": "clock",
    "Contacts": "contacts",
    "Expense": "pro expense",
    "Files": "files",
    "Joplin": "joplin",
    "Markor": "markor",
    "Osmand": "osmand",
    "OpenTracks": "opentracks",
    "Recipe": "broccoli",
    "RetroMusic": "retro music",
    "Settings": "settings",
    "SimpleCalendar": "simple calendar pro",
    "SimpleDraw": "simple draw pro",
    "SimpleGallery": "simple gallery pro",
    "SimpleSms": "simple sms messenger",
    "Sms": "simple sms messenger",
    "Tasks": "tasks",
    "Vlc": "vlc",
}


def _infer_app_from_task(task_name: str) -> str:
    """从任务名推断所属应用。"""
    for prefix, app_name in TASK_PREFIX_TO_APP.items():
        if task_name.startswith(prefix):
            return app_name
    return "unknown"


def _get_package_id(app_name: str) -> str:
    """获取应用的包名。"""
    return APP_PACKAGE_MAP.get(app_name.lower(), app_name)


def _make_page_id(app_id: str, page_name: str) -> str:
    """生成确定性的页面ID。"""
    raw = f"{app_id}:{page_name}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def bootstrap_static(kg_client, metadata_path: str = "") -> dict:
    """从task_metadata.json静态构建KG。

    不需要模拟器，仅从任务元数据中提取:
    - 每个应用注册为App
    - 每个应用的首页注册为Page
    - 每个任务的goal模板注册为Intent

    Args:
        kg_client: KGClient实例
        metadata_path: task_metadata.json的路径

    Returns:
        dict: 统计信息 {apps, pages, intents}
    """
    if not metadata_path:
        # 默认路径
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        metadata_path = os.path.join(base, "task_metadata.json")

    if not os.path.exists(metadata_path):
        logger.error(f"未找到 task_metadata.json: {metadata_path}")
        return {"apps": 0, "pages": 0, "intents": 0}

    with open(metadata_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    stats = {"apps": 0, "pages": 0, "intents": 0}
    registered_apps = set()

    for task in tasks:
        task_name = task.get("task_name", "")
        task_template = task.get("task_template", "")
        app_name = _infer_app_from_task(task_name)
        app_id = _get_package_id(app_name)

        # 注册应用和首页
        if app_id not in registered_apps:
            try:
                kg_client.add_page(
                    app_id=app_id,
                    page_name=f"{app_name}_home",
                    page_type="home",
                    description=f"{app_name} application home page",
                )
                registered_apps.add(app_id)
                stats["apps"] += 1
                stats["pages"] += 1
            except Exception as e:
                logger.debug(f"注册应用 {app_name} 失败: {e}")

        # 注册任务意图
        if task_template:
            try:
                # 清理模板中的占位符
                clean_template = task_template
                import re
                clean_template = re.sub(r'\{[^}]+\}', '...', clean_template)

                kg_client.register_intent(
                    app_id=app_id,
                    intent_text=clean_template,
                    keywords=[task_name],
                )
                stats["intents"] += 1
            except Exception as e:
                logger.debug(f"注册意图 {task_name} 失败: {e}")

    logger.info(
        f"静态预建完成: {stats['apps']}个应用, "
        f"{stats['pages']}个页面, {stats['intents']}个意图"
    )
    return stats


def bootstrap_from_exploration(
    kg_client,
    env,
    app_names: list = None,
    steps_per_app: int = 30,
) -> dict:
    """通过模拟器动态探索构建KG。

    对每个应用:
    1. 打开应用
    2. 执行随机可交互操作
    3. 记录每个状态为KG页面
    4. 记录状态转换为KG转换

    Args:
        kg_client: KGClient实例
        env: AndroidWorld AsyncEnv实例
        app_names: 要探索的应用列表（默认ALL_APPS的前缀）
        steps_per_app: 每个应用的探索步数

    Returns:
        dict: 统计信息
    """
    from android_world.bridge.page_abstractor import (
        state_to_ui_hierarchy,
        extract_page_title,
        detect_app_id,
        describe_page,
    )
    from android_world.env import adb_utils

    if app_names is None:
        app_names = list(APP_PACKAGE_MAP.keys())

    stats = {"apps": 0, "pages": 0, "transitions": 0, "errors": 0}
    seen_pages = {}  # (app_id, page_hash) -> page_id

    for app_name in app_names:
        app_id = _get_package_id(app_name)
        logger.info(f"\n探索应用: {app_name} ({app_id})")

        # 启动应用
        try:
            adb_utils.launch_app(app_name, env.controller)
            import time
            time.sleep(3)
        except Exception as e:
            logger.warning(f"  启动 {app_name} 失败: {e}")
            stats["errors"] += 1
            continue

        stats["apps"] += 1
        prev_page_id = None

        for step in range(steps_per_app):
            try:
                state = env.get_state(wait_to_stabilize=False)

                # 提取页面信息
                ui_hierarchy = state_to_ui_hierarchy(state)
                page_title = extract_page_title(state)
                page_desc = describe_page(state)

                # 计算页面哈希用于去重
                hierarchy_str = json.dumps(
                    [w.get("class", "") + w.get("resource-id", "")
                     for w in ui_hierarchy.get("children", [])],
                    sort_keys=True,
                )
                page_hash = hashlib.md5(hierarchy_str.encode()).hexdigest()[:12]

                page_key = (app_id, page_hash)
                if page_key not in seen_pages:
                    # 新页面，注册到KG
                    page_name = page_title or f"page_{page_hash[:6]}"
                    try:
                        page_id = kg_client.add_page(
                            app_id=app_id,
                            page_name=page_name,
                            page_type="other",
                            description=page_desc,
                            ui_hierarchy=ui_hierarchy,
                        )
                        seen_pages[page_key] = page_id
                        stats["pages"] += 1
                        logger.debug(f"  新页面: {page_name}")
                    except Exception as e:
                        seen_pages[page_key] = _make_page_id(app_id, page_name)
                        logger.debug(f"  注册页面失败: {e}")

                current_page_id = seen_pages[page_key]

                # 记录转换
                if prev_page_id and prev_page_id != current_page_id:
                    try:
                        kg_client.report_transition(
                            from_page=prev_page_id,
                            action={"type": "click"},
                            to_page=current_page_id,
                            success=True,
                        )
                        stats["transitions"] += 1
                    except Exception:
                        pass

                prev_page_id = current_page_id

                # 选择随机可交互元素执行操作
                clickable = [
                    e for e in (state.ui_elements or [])
                    if getattr(e, "is_clickable", False)
                    and getattr(e, "is_visible", True)
                    and getattr(e, "bbox_pixels", None)
                ]
                if not clickable:
                    break

                elem = random.choice(clickable)
                bp = elem.bbox_pixels
                cx = int((bp.x_min + bp.x_max) / 2)
                cy = int((bp.y_min + bp.y_max) / 2)

                from android_world.agents.new_json_action import JSONAction
                action = JSONAction(
                    action_type="click",
                    index=None, x=cx, y=cy,
                    text=None, direction=None,
                    goal_status=None, app_name=None, keycode=None,
                )
                env.execute_action(action)
                import time
                time.sleep(2)

            except Exception as e:
                logger.debug(f"  步骤{step}异常: {e}")
                stats["errors"] += 1
                # 尝试返回
                try:
                    from android_world.agents.new_json_action import JSONAction
                    back_action = JSONAction(
                        action_type="navigate_back",
                        index=None, x=None, y=None,
                        text=None, direction=None,
                        goal_status=None, app_name=None, keycode=None,
                    )
                    env.execute_action(back_action)
                    import time
                    time.sleep(1)
                except Exception:
                    pass

    logger.info(
        f"\n动态探索完成: {stats['apps']}个应用, "
        f"{stats['pages']}个页面, {stats['transitions']}个转换, "
        f"{stats['errors']}个错误"
    )
    return stats


def save_kg(kg_client, output_dir: str):
    """将KG数据导出到目录。

    Args:
        kg_client: KGClient实例
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        data = kg_client.export_graph()
        output_path = os.path.join(output_dir, "kg_graph.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"KG数据已导出到: {output_path}")
    except Exception as e:
        logger.error(f"导出KG失败: {e}")

    # 保存统计信息
    try:
        stats = kg_client.get_graph_stats()
        stats_path = os.path.join(output_dir, "kg_stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main():
    """命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="AndroidWorld KG预建工具")
    parser.add_argument("--mode", choices=["static", "explore", "both"],
                        default="static", help="预建模式")
    parser.add_argument("--output", default="kg_data/", help="输出目录")
    parser.add_argument("--steps", type=int, default=30, help="每个应用的探索步数")
    parser.add_argument("--kg-project-path", default="", help="KG项目路径")
    parser.add_argument("--metadata", default="", help="task_metadata.json路径")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # 导入KGClient
    if args.kg_project_path:
        sys.path.insert(0, args.kg_project_path)
    try:
        from agent_interface.kg_client import KGClient
    except ImportError:
        logger.error(
            "无法导入KGClient。请通过 --kg-project-path 指定"
            "HarmonyOS-App-Testing-Knowledge-Graph 项目路径。"
        )
        sys.exit(1)

    kg = KGClient()

    if args.mode in ("static", "both"):
        logger.info("=== 静态预建 ===")
        bootstrap_static(kg, metadata_path=args.metadata)

    if args.mode in ("explore", "both"):
        logger.info("=== 动态探索 ===")
        logger.info("动态探索需要运行中的Android模拟器，请通过 run_ma3.py 框架调用。")
        logger.info("或在代码中直接调用 bootstrap_from_exploration(kg, env)")

    save_kg(kg, args.output)
    logger.info(f"\n完成! KG数据已保存到 {args.output}")


if __name__ == "__main__":
    main()
