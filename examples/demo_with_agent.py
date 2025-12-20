#!/usr/bin/env python3
"""
示例：与GUI Agent对接

这个示例展示如何将知识图谱集成到GUI Agent中:
1. Agent如何查询操作路径
2. Agent如何根据意图获取下一步操作
3. Agent如何上报执行结果更新图谱
4. 完整的测试执行流程模拟
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
from dataclasses import dataclass
from agent_interface.kg_client import KGClient, ActionRecommendation


# ============================================================
# 模拟的GUI Agent
# ============================================================

@dataclass
class UIElement:
    """模拟的UI元素"""
    widget_id: str
    widget_type: str
    text: str
    clickable: bool = True


@dataclass 
class PageState:
    """模拟的页面状态"""
    page_id: str
    page_name: str
    elements: List[UIElement]


class MockGUIAgent:
    """
    模拟的GUI Agent
    
    展示如何与知识图谱集成
    """
    
    def __init__(self, kg_client: KGClient, app_id: str):
        self.kg = kg_client
        self.app_id = app_id
        self.current_page: Optional[PageState] = None
        self.action_history: List[Dict] = []
    
    def set_current_page(self, page: PageState):
        """设置当前页面（模拟屏幕状态）"""
        self.current_page = page
        print(f"📱 当前页面: {page.page_name}")
    
    def execute_task(self, intent: str) -> bool:
        """
        执行测试任务
        
        这是Agent的核心方法，展示了与KG的完整交互流程
        """
        print(f"\n{'='*60}")
        print(f"🎯 执行任务: {intent}")
        print(f"{'='*60}")
        
        if not self.current_page:
            print("❌ 错误: 未设置当前页面")
            return False
        
        # 步骤1: 查询完整路径
        print("\n[Step 1] 查询操作路径...")
        path_result = self.kg.query_path(
            app_id=self.app_id,
            intent=intent,
            current_page=self.current_page.page_id
        )
        
        if not path_result["success"]:
            print(f"❌ 路径查询失败: {path_result['message']}")
            return False
        
        path = path_result["path"]
        print(f"✓ 找到路径，共 {path['total_steps']} 步")
        print(f"  置信度: {path_result['confidence']:.2f}")
        
        # 步骤2: 逐步执行
        print("\n[Step 2] 开始执行操作序列...")
        
        for step in path["steps"]:
            print(f"\n  --- 步骤 {step['step']} ---")
            print(f"  操作: {step['action']}")
            print(f"  控件: {step['widget_text']}")
            
            # 执行操作（模拟）
            success = self._execute_action(step)
            
            # 上报执行结果
            self.kg.report_transition(
                from_page=self.current_page.page_id,
                action={
                    "type": step["action"],
                    "widget": step["widget_id"],
                    "widget_text": step["widget_text"]
                },
                to_page=step["expected_page"],
                success=success,
                latency_ms=150
            )
            
            if not success:
                print(f"  ❌ 执行失败")
                return False
            
            print(f"  ✓ 执行成功")
            
            # 模拟页面切换
            self._simulate_page_transition(step["expected_page"])
        
        print(f"\n{'='*60}")
        print(f"✅ 任务完成!")
        print(f"{'='*60}")
        return True
    
    def execute_with_realtime_guidance(self, intent: str, max_steps: int = 10) -> bool:
        """
        使用实时引导执行任务
        
        每一步都向KG查询下一步操作，适用于动态环境
        """
        print(f"\n{'='*60}")
        print(f"🎯 实时引导模式: {intent}")
        print(f"{'='*60}")
        
        for step_num in range(max_steps):
            print(f"\n--- 步骤 {step_num + 1} ---")
            
            # 查询下一步操作
            next_action = self.kg.get_next_action(
                current_page=self.current_page.page_id,
                intent=intent
            )
            
            if not next_action:
                # 检查是否已到达目标
                print("✓ 已到达目标或无更多操作")
                return True
            
            print(f"推荐操作: {next_action.action_type} on '{next_action.widget_text}'")
            print(f"置信度: {next_action.confidence:.2f}")
            
            # 执行操作
            success = self._execute_action({
                "action": next_action.action_type,
                "widget_id": next_action.widget_id,
                "widget_text": next_action.widget_text
            })
            
            if not success:
                print("❌ 执行失败，尝试恢复...")
                # 这里可以添加恢复逻辑
                return False
            
            # 更新页面状态
            self._simulate_page_transition(next_action.expected_page)
            
            # 检查是否完成
            if next_action.expected_page == self.current_page.page_id:
                # 可能是目标页面
                pass
        
        print("⚠️ 达到最大步骤数")
        return False
    
    def explore_and_learn(self, max_actions: int = 20):
        """
        探索模式：自由探索并学习
        
        用于新App的冷启动
        """
        print(f"\n{'='*60}")
        print(f"🔍 探索模式")
        print(f"{'='*60}")
        
        for i in range(max_actions):
            print(f"\n--- 探索 {i+1}/{max_actions} ---")
            
            # 获取当前页面可用操作
            actions = self.kg.get_available_actions(self.current_page.page_id)
            
            if not actions:
                print("无可用操作，随机点击...")
                # 实际实现中这里会随机选择屏幕元素
                break
            
            # 选择一个未充分探索的操作
            action = self._select_exploration_action(actions)
            
            print(f"探索: {action.get('trigger_widget_text', 'unknown')}")
            
            # 执行并记录
            # ...
    
    def _execute_action(self, step: Dict) -> bool:
        """模拟执行操作"""
        # 在实际实现中，这里会调用设备API执行操作
        # 例如: adb shell input tap x y
        return True  # 模拟成功
    
    def _simulate_page_transition(self, target_page_id: str):
        """模拟页面切换"""
        # 在实际实现中，这里会等待页面加载并获取新页面状态
        self.current_page = PageState(
            page_id=target_page_id,
            page_name=target_page_id.split(":")[-1] if ":" in target_page_id else target_page_id,
            elements=[]
        )
        print(f"  → 跳转到: {self.current_page.page_name}")
    
    def _select_exploration_action(self, actions: List[Dict]) -> Dict:
        """选择探索操作（优先选择成功率低的）"""
        # 简单实现：返回第一个
        return actions[0] if actions else {}


# ============================================================
# 演示
# ============================================================

def setup_demo_graph():
    """设置演示用的图谱（复用之前的构建代码）"""
    from examples.demo_build_graph import build_meituan_graph
    return build_meituan_graph()


def demo_basic_integration():
    """演示基本集成"""
    print("\n" + "=" * 70)
    print("演示1: 基本Agent集成")
    print("=" * 70)
    
    # 设置图谱
    graph, vectors, embedder, page_ids = setup_demo_graph()
    
    # 创建KG客户端
    kg = KGClient(
        graph_store=graph,
        vector_store=vectors,
        embedding_model=embedder
    )
    
    # 创建Agent
    agent = MockGUIAgent(kg, "com.meituan.app")
    
    # 设置初始页面
    agent.set_current_page(PageState(
        page_id=page_ids["首页"],
        page_name="首页",
        elements=[]
    ))
    
    # 执行任务
    agent.execute_task("点外卖")


def demo_realtime_guidance():
    """演示实时引导模式"""
    print("\n" + "=" * 70)
    print("演示2: 实时引导模式")
    print("=" * 70)
    
    graph, vectors, embedder, page_ids = setup_demo_graph()
    
    kg = KGClient(
        graph_store=graph,
        vector_store=vectors,
        embedding_model=embedder
    )
    
    agent = MockGUIAgent(kg, "com.meituan.app")
    agent.set_current_page(PageState(
        page_id=page_ids["首页"],
        page_name="首页",
        elements=[]
    ))
    
    agent.execute_with_realtime_guidance("查找附近餐厅")


def demo_integration_code():
    """
    展示实际Agent集成的代码模板
    """
    print("\n" + "=" * 70)
    print("Agent集成代码模板")
    print("=" * 70)
    
    code = '''
# ==================== 在你的GUI Agent中集成知识图谱 ====================

from agent_interface import KGClient

class YourGUIAgent:
    def __init__(self):
        # 初始化知识图谱客户端
        self.kg = KGClient()
        # 或使用远程API
        # self.kg = KGClient(api_endpoint="http://localhost:8000")
    
    def execute_test_task(self, app_id: str, task: str):
        """执行测试任务"""
        
        # 1. 获取当前页面ID（从你的页面识别模块）
        current_page = self.get_current_page_id()
        
        # 2. 查询操作路径
        result = self.kg.query_path(
            app_id=app_id,
            intent=task,
            current_page=current_page
        )
        
        if not result["success"]:
            self.handle_no_path(task)
            return
        
        # 3. 逐步执行
        for step in result["path"]["steps"]:
            # 定位控件
            widget = self.find_widget(step["widget_id"], step["widget_text"])
            
            # 执行操作
            success = self.perform_action(step["action"], widget)
            
            # 上报结果（用于图谱学习）
            self.kg.report_transition(
                from_page=current_page,
                action={"type": step["action"], "widget": step["widget_id"]},
                to_page=step["expected_page"],
                success=success
            )
            
            if not success:
                # 处理失败
                break
            
            # 等待页面加载
            self.wait_for_page_load()
            current_page = self.get_current_page_id()
    
    def execute_with_kg_guidance(self, task: str):
        """使用KG实时引导（适合动态环境）"""
        
        while not self.is_task_complete(task):
            current_page = self.get_current_page_id()
            
            # 获取下一步推荐
            action = self.kg.get_next_action(current_page, task)
            
            if not action:
                break
            
            # 执行推荐操作
            self.perform_action(action.action_type, action.widget_id)
    
    def get_llm_context(self, task: str) -> str:
        """获取RAG上下文供LLM决策使用"""
        context = self.kg.get_rag_context(
            app_id=self.app_id,
            query=task,
            current_page=self.current_page_id
        )
        return context["prompt"]
'''
    print(code)


def main():
    """主函数"""
    # demo_basic_integration()
    # demo_realtime_guidance()
    demo_integration_code()


if __name__ == "__main__":
    main()
