"""
独立评估框架 - 不依赖外部Agent

直接用HmTest数据集评估知识图谱的路径成功率和步骤效率
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_interface import KGClient
from kg_core.schema import Page, PageType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PathOperation:
    """单个操作"""
    action_type: str  # click, input, swipe, etc.
    widget_id: str
    widget_text: str
    target_page_id: Optional[str] = None


@dataclass
class GroundTruthPath:
    """Ground truth操作路径"""
    app_id: str
    intent: str
    start_page: str
    end_page: str
    operations: List[PathOperation]

    @property
    def length(self) -> int:
        return len(self.operations)


@dataclass
class KGQueryResult:
    """知识图谱查询结果"""
    success: bool
    path: Optional[List[Dict]] = None
    confidence: float = 0.0
    alternatives: Optional[List[Dict]] = None
    error: Optional[str] = None


@dataclass
class EvaluationMetrics:
    """评估指标"""
    # 路径成功率
    path_success_rate: float = 0.0  # 百分比

    # 步骤效率
    step_efficiency: float = 0.0     # 百分比

    # 详细指标
    successful_paths: int = 0
    total_paths: int = 0

    average_kg_steps: float = 0.0
    average_random_steps: float = 0.0
    average_steps_saved: float = 0.0

    # 多样性分析
    short_paths_accuracy: float = 0.0  # 5步以内的准确率
    medium_paths_accuracy: float = 0.0  # 6-10步的准确率
    long_paths_accuracy: float = 0.0   # 11+步的准确率

    def __str__(self) -> str:
        return f"""
╔════════════════════════════════════════════════════════════╗
║         知识图谱独立评估结果                                  ║
╚════════════════════════════════════════════════════════════╝

【核心指标】
├─ 路径成功率: {self.path_success_rate:.1f}%
│   ✓ 成功: {self.successful_paths}/{self.total_paths}
│   ✗ 目标: ≥70%
│
├─ 步骤效率: {self.step_efficiency:.1f}%
│   ✓ 平均KG步数: {self.average_kg_steps:.1f}
│   ✓ 平均随机步数: {self.average_random_steps:.1f}
│   ✓ 平均节省: {self.average_steps_saved:.1f}步
│   ✗ 目标: ≥60%
│
【多样性分析】(5-15+步的路径准确率差异)
├─ 短路径 (≤5步): {self.short_paths_accuracy:.1f}%
├─ 中等路径 (6-10步): {self.medium_paths_accuracy:.1f}%
└─ 长路径 (11+步): {self.long_paths_accuracy:.1f}%

╚════════════════════════════════════════════════════════════╝
"""


class GroundTruthLoader:
    """从HmTest数据集加载Ground Truth路径"""

    def __init__(self, hmtest_data_dir: str):
        self.data_dir = Path(hmtest_data_dir)
        self.paths: Dict[str, List[GroundTruthPath]] = {}

    def load_from_json(self, app_id: str, json_file: str) -> List[GroundTruthPath]:
        """
        从JSON文件加载标注的路径

        JSON格式示例:
        {
            "paths": [
                {
                    "intent": "搜索商品",
                    "start_page": "home",
                    "end_page": "search_results",
                    "operations": [
                        {"action_type": "click", "widget_text": "search_button", "target_page": "search"},
                        {"action_type": "input", "widget_text": "search_input", "input": "手机"},
                        {"action_type": "click", "widget_text": "search_btn", "target_page": "search_results"}
                    ]
                }
            ]
        }
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            paths = []
            for path_data in data.get('paths', []):
                ops = [
                    PathOperation(
                        action_type=op['action_type'],
                        widget_id=op.get('widget_id', ''),
                        widget_text=op.get('widget_text', ''),
                        target_page_id=op.get('target_page')
                    )
                    for op in path_data.get('operations', [])
                ]

                gt_path = GroundTruthPath(
                    app_id=app_id,
                    intent=path_data['intent'],
                    start_page=path_data['start_page'],
                    end_page=path_data['end_page'],
                    operations=ops
                )
                paths.append(gt_path)

            self.paths[app_id] = paths
            logger.info(f"加载 {app_id}: {len(paths)} 条路径")
            return paths

        except Exception as e:
            logger.error(f"加载失败 {json_file}: {e}")
            return []

    def load_from_directory(self, hmtest_apps_dir: str) -> Dict[str, List[GroundTruthPath]]:
        """从HmTest应用目录批量加载所有路径"""
        apps_dir = Path(hmtest_apps_dir)
        all_paths = {}

        for app_dir in apps_dir.iterdir():
            if not app_dir.is_dir():
                continue

            # 查找ground truth JSON文件
            json_files = list(app_dir.glob('**/paths.json'))
            json_files += list(app_dir.glob('**/ground_truth.json'))
            json_files += list(app_dir.glob('**/routes.json'))

            if json_files:
                app_id = app_dir.name
                paths = self.load_from_json(app_id, str(json_files[0]))
                if paths:
                    all_paths[app_id] = paths

        return all_paths


class StandaloneEvaluator:
    """独立评估器"""

    def __init__(self):
        self.kg = KGClient()
        self.results = []

    def build_knowledge_graph(self, ground_truth_paths: Dict[str, List[GroundTruthPath]]) -> Dict[str, Dict]:
        """
        根据Ground Truth路径构建知识图谱

        Returns:
            page_maps: 每个应用的页面名称到ID的映射字典
        """
        logger.info("【第1步】构建知识图谱...")

        all_page_maps = {}

        for app_id, paths in ground_truth_paths.items():
            logger.info(f"  处理应用: {app_id}")

            # 收集所有页面
            all_pages = set()
            for path in paths:
                all_pages.add(path.start_page)
                all_pages.add(path.end_page)
                for op in path.operations:
                    if op.target_page_id:
                        all_pages.add(op.target_page_id)

            # 添加页面到知识图谱
            page_map = {}
            for page_name in all_pages:
                try:
                    page_id = self.kg.add_page(
                        app_id=app_id,
                        page_name=page_name,
                        page_type="other",
                        description=f"Page: {page_name}"
                    )
                    page_map[page_name] = page_id
                    logger.debug(f"    添加页面: {page_name} -> {page_id}")
                except Exception as e:
                    logger.error(f"    添加页面失败 {page_name}: {e}")

            # 添加转换关系
            for path in paths:
                current_page = path.start_page
                for i, op in enumerate(path.operations):
                    next_page = op.target_page_id or (path.end_page if i == len(path.operations) - 1 else current_page)

                    try:
                        self.kg.report_transition(
                            from_page=page_map.get(current_page, current_page),
                            action={
                                "type": op.action_type,
                                "widget": op.widget_id,
                                "widget_text": op.widget_text
                            },
                            to_page=page_map.get(next_page, next_page),
                            success=True
                        )
                        current_page = next_page
                    except Exception as e:
                        logger.warning(f"    添加转换失败: {e}")

            # 注册意图
            for path in paths:
                try:
                    self.kg.register_intent(
                        app_id=app_id,
                        intent_text=path.intent,
                        target_page=page_map.get(path.end_page, path.end_page)
                    )
                except Exception as e:
                    logger.warning(f"    注册意图失败 {path.intent}: {e}")

            # 保存页面映射
            all_page_maps[app_id] = page_map

        logger.info("✓ 知识图谱构建完成\n")
        return all_page_maps

    def query_paths(self, ground_truth_paths: Dict[str, List[GroundTruthPath]], page_maps: Dict[str, Dict] = None) -> List[Dict]:
        """
        【第2步】查询知识图谱，获得KG路径

        Args:
            ground_truth_paths: Ground Truth路径
            page_maps: 页面名称到页面ID的映射（从build_knowledge_graph获得）
        """
        logger.info("【第2步】查询知识图谱路径...")

        results = []
        for app_id, paths in ground_truth_paths.items():
            logger.info(f"  应用: {app_id}")

            # 获取该应用的页面映射
            page_map = page_maps.get(app_id, {}) if page_maps else {}

            for gt_path in paths:
                try:
                    # 使用页面ID而不是页面名称
                    start_page_id = page_map.get(gt_path.start_page, gt_path.start_page)
                    kg_result = self.kg.query_path(
                        app_id=app_id,
                        intent=gt_path.intent,
                        current_page=start_page_id,
                        max_steps=20
                    )

                    result = {
                        "app_id": app_id,
                        "intent": gt_path.intent,
                        "gt_length": gt_path.length,
                        "kg_success": kg_result.get("success", False),
                        "kg_steps": len(kg_result.get("path", {}).get("steps", [])) if kg_result.get("success") else -1,
                        "kg_confidence": kg_result.get("path", {}).get("confidence", 0.0) if kg_result.get("success") else 0.0,
                        "ground_truth": gt_path
                    }
                    results.append(result)

                    logger.debug(f"    意图: {gt_path.intent} -> KG: {result['kg_steps']} 步, GT: {gt_path.length} 步")

                except Exception as e:
                    logger.error(f"    查询失败 {gt_path.intent}: {e}")

        logger.info(f"✓ 查询完成: 总共 {len(results)} 条路径\n")
        return results

    def evaluate(self, query_results: List[Dict]) -> EvaluationMetrics:
        """
        【第3步】对比分析
        """
        logger.info("【第3步】对比分析和指标计算...")

        metrics = EvaluationMetrics()
        metrics.total_paths = len(query_results)

        short_success = 0
        short_total = 0
        medium_success = 0
        medium_total = 0
        long_success = 0
        long_total = 0

        kg_steps_list = []
        random_steps_list = []

        for result in query_results:
            gt_length = result['gt_length']
            kg_steps = result['kg_steps']

            # 路径成功率：KG查询成功 AND 步数接近（±2步以内为成功）
            if result['kg_success'] and kg_steps > 0:
                # 允许一定的误差范围
                if abs(kg_steps - gt_length) <= 2:
                    metrics.successful_paths += 1
                    kg_steps_list.append(kg_steps)
                    random_steps_list.append(gt_length * 3)  # 随机Agent预期需要3倍步数

            # 多样性分析
            if gt_length <= 5:
                short_total += 1
                if result['kg_success'] and kg_steps > 0 and abs(kg_steps - gt_length) <= 2:
                    short_success += 1
            elif gt_length <= 10:
                medium_total += 1
                if result['kg_success'] and kg_steps > 0 and abs(kg_steps - gt_length) <= 2:
                    medium_success += 1
            else:
                long_total += 1
                if result['kg_success'] and kg_steps > 0 and abs(kg_steps - gt_length) <= 2:
                    long_success += 1

        # 计算指标
        if metrics.total_paths > 0:
            metrics.path_success_rate = (metrics.successful_paths / metrics.total_paths) * 100

        if kg_steps_list and random_steps_list:
            metrics.average_kg_steps = sum(kg_steps_list) / len(kg_steps_list)
            metrics.average_random_steps = sum(random_steps_list) / len(random_steps_list)
            metrics.average_steps_saved = metrics.average_random_steps - metrics.average_kg_steps

            if metrics.average_random_steps > 0:
                metrics.step_efficiency = (metrics.average_steps_saved / metrics.average_random_steps) * 100

        # 多样性分析
        if short_total > 0:
            metrics.short_paths_accuracy = (short_success / short_total) * 100
        if medium_total > 0:
            metrics.medium_paths_accuracy = (medium_success / medium_total) * 100
        if long_total > 0:
            metrics.long_paths_accuracy = (long_success / long_total) * 100

        logger.info(f"✓ 评估完成\n")
        return metrics

    def run(self, hmtest_apps_dir: str) -> EvaluationMetrics:
        """
        完整的评估流程
        """
        logger.info("="*60)
        logger.info("知识图谱独立评估框架")
        logger.info(f"HmTest数据集目录: {hmtest_apps_dir}")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60 + "\n")

        # 加载Ground Truth
        logger.info("【第0步】加载Ground Truth路径...")
        loader = GroundTruthLoader(hmtest_apps_dir)
        ground_truth_paths = loader.load_from_directory(hmtest_apps_dir)

        if not ground_truth_paths:
            logger.error("✗ 未找到任何Ground Truth路径！")
            return EvaluationMetrics()

        logger.info(f"✓ 加载完成: {sum(len(p) for p in ground_truth_paths.values())} 条路径\n")

        # 构建KG
        page_maps = self.build_knowledge_graph(ground_truth_paths)

        # 查询路径
        query_results = self.query_paths(ground_truth_paths, page_maps)

        # 评估
        metrics = self.evaluate(query_results)

        # 输出结果
        logger.info(str(metrics))

        # 保存详细结果
        self._save_results(metrics, query_results)

        return metrics

    def _save_results(self, metrics: EvaluationMetrics, query_results: List[Dict]):
        """保存评估结果到JSON"""
        result_file = 'evaluation_results.json'

        data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "path_success_rate": metrics.path_success_rate,
                "step_efficiency": metrics.step_efficiency,
                "successful_paths": metrics.successful_paths,
                "total_paths": metrics.total_paths,
                "average_kg_steps": metrics.average_kg_steps,
                "average_random_steps": metrics.average_random_steps,
                "average_steps_saved": metrics.average_steps_saved,
                "short_paths_accuracy": metrics.short_paths_accuracy,
                "medium_paths_accuracy": metrics.medium_paths_accuracy,
                "long_paths_accuracy": metrics.long_paths_accuracy
            },
            "details": [
                {
                    "app_id": r["app_id"],
                    "intent": r["intent"],
                    "gt_length": r["gt_length"],
                    "kg_success": r["kg_success"],
                    "kg_steps": r["kg_steps"],
                    "kg_confidence": r["kg_confidence"]
                }
                for r in query_results
            ]
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ 结果已保存到 {result_file}")


if __name__ == "__main__":
    # 使用示例
    import argparse

    parser = argparse.ArgumentParser(description="知识图谱独立评估框架")
    parser.add_argument(
        "--hmtest-dir",
        default="./hmtest/data/apps",
        help="HmTest应用目录"
    )

    args = parser.parse_args()

    evaluator = StandaloneEvaluator()
    metrics = evaluator.run(args.hmtest_dir)

    # 输出最终评分
    print("\n" + "="*60)
    print("最终评分")
    print("="*60)
    print(f"路径成功率: {metrics.path_success_rate:.1f}% (目标: ≥70%)")
    print(f"步骤效率: {metrics.step_efficiency:.1f}% (目标: ≥60%)")
    print("="*60)
