"""
图数据库操作模块

支持两种模式:
1. memory: 使用NetworkX的内存图 (用于Demo和测试)
2. neo4j: 使用Neo4j图数据库 (生产环境)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import networkx as nx

from .schema import Page, Widget, Transition, App, ActionType


@dataclass
class PathResult:
    """路径查询结果"""
    pages: List[str]               # 页面ID序列
    transitions: List[Dict]        # 转换详情
    total_steps: int
    
    def to_dict(self) -> Dict:
        return {
            "pages": self.pages,
            "transitions": self.transitions,
            "total_steps": self.total_steps
        }


class BaseGraphStore(ABC):
    """图存储抽象基类"""
    
    @abstractmethod
    def add_page(self, page: Page) -> bool:
        pass
    
    @abstractmethod
    def add_transition(self, transition: Transition) -> bool:
        pass
    
    @abstractmethod
    def get_page(self, page_id: str) -> Optional[Page]:
        pass
    
    @abstractmethod
    def find_shortest_path(self, start_id: str, end_id: str) -> Optional[PathResult]:
        pass
    
    @abstractmethod
    def get_outgoing_transitions(self, page_id: str) -> List[Transition]:
        pass


class MemoryGraphStore(BaseGraphStore):
    """
    内存图存储 (基于NetworkX)
    
    适用于Demo和测试，无需外部数据库
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.pages: Dict[str, Page] = {}
        self.transitions: Dict[str, Transition] = {}
        self.apps: Dict[str, App] = {}
    
    def add_app(self, app: App) -> bool:
        """添加应用"""
        self.apps[app.app_id] = app
        return True
    
    def add_page(self, page: Page) -> bool:
        """添加页面节点"""
        self.pages[page.page_id] = page
        self.graph.add_node(
            page.page_id,
            **page.to_dict()
        )
        return True
    
    def add_transition(self, transition: Transition) -> bool:
        """添加转换边"""
        self.transitions[transition.transition_id] = transition
        self.graph.add_edge(
            transition.source_page_id,
            transition.target_page_id,
            **transition.to_dict()
        )
        return True
    
    def get_page(self, page_id: str) -> Optional[Page]:
        """获取页面"""
        return self.pages.get(page_id)
    
    def get_all_pages(self, app_id: str = None) -> List[Page]:
        """获取所有页面"""
        if app_id:
            return [p for p in self.pages.values() if p.app_id == app_id]
        return list(self.pages.values())
    
    def get_transition(self, source_id: str, target_id: str) -> Optional[Transition]:
        """获取特定转换"""
        for t in self.transitions.values():
            if t.source_page_id == source_id and t.target_page_id == target_id:
                return t
        return None
    
    def find_shortest_path(self, start_id: str, end_id: str) -> Optional[PathResult]:
        """查找最短路径"""
        try:
            path = nx.shortest_path(self.graph, start_id, end_id)
            transitions = []
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i+1])
                if edge_data:
                    transitions.append(edge_data)
            return PathResult(
                pages=path,
                transitions=transitions,
                total_steps=len(path) - 1
            )
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None
    
    def find_all_paths(self, start_id: str, end_id: str, max_length: int = 10) -> List[PathResult]:
        """查找所有路径（限制长度）"""
        try:
            paths = list(nx.all_simple_paths(
                self.graph, start_id, end_id, cutoff=max_length
            ))
            results = []
            for path in paths[:5]:  # 最多返回5条
                transitions = []
                for i in range(len(path) - 1):
                    edge_data = self.graph.get_edge_data(path[i], path[i+1])
                    if edge_data:
                        transitions.append(edge_data)
                results.append(PathResult(
                    pages=path,
                    transitions=transitions,
                    total_steps=len(path) - 1
                ))
            return results
        except:
            return []
    
    def get_outgoing_transitions(self, page_id: str) -> List[Transition]:
        """获取页面的所有出边（可达页面）"""
        result = []
        for t in self.transitions.values():
            if t.source_page_id == page_id:
                result.append(t)
        return result
    
    def get_incoming_transitions(self, page_id: str) -> List[Transition]:
        """获取页面的所有入边"""
        result = []
        for t in self.transitions.values():
            if t.target_page_id == page_id:
                result.append(t)
        return result
    
    def find_page_by_name(self, page_name: str, app_id: str = None) -> Optional[Page]:
        """按名称查找页面"""
        for page in self.pages.values():
            if page.page_name == page_name:
                if app_id is None or page.app_id == app_id:
                    return page
        return None
    
    def get_reachable_pages(self, start_id: str, max_depth: int = 5) -> List[str]:
        """获取从某页面可达的所有页面"""
        try:
            # BFS遍历
            visited = set()
            queue = [(start_id, 0)]
            
            while queue:
                page_id, depth = queue.pop(0)
                if page_id in visited or depth > max_depth:
                    continue
                visited.add(page_id)
                
                for successor in self.graph.successors(page_id):
                    if successor not in visited:
                        queue.append((successor, depth + 1))
            
            return list(visited)
        except:
            return [start_id]
    
    def update_transition_stats(self, transition_id: str, success: bool, latency_ms: int = 0):
        """更新转换统计信息"""
        if transition_id in self.transitions:
            t = self.transitions[transition_id]
            if success:
                t.success_count += 1
            else:
                t.fail_count += 1
            # 更新平均延迟
            total = t.success_count + t.fail_count
            t.avg_latency_ms = int((t.avg_latency_ms * (total - 1) + latency_ms) / total)
    
    def get_graph_stats(self) -> Dict:
        """获取图谱统计信息"""
        return {
            "total_apps": len(self.apps),
            "total_pages": len(self.pages),
            "total_transitions": len(self.transitions),
            "avg_out_degree": sum(self.graph.out_degree(n) for n in self.graph.nodes()) / max(len(self.pages), 1)
        }
    
    def export_to_dict(self) -> Dict:
        """导出图谱为字典格式"""
        return {
            "apps": [a.to_dict() for a in self.apps.values()],
            "pages": [p.to_dict() for p in self.pages.values()],
            "transitions": [t.to_dict() for t in self.transitions.values()]
        }
    
    def clear(self):
        """清空图谱"""
        self.graph.clear()
        self.pages.clear()
        self.transitions.clear()
        self.apps.clear()


class Neo4jGraphStore(BaseGraphStore):
    """
    Neo4j图存储
    
    生产环境使用，需要Neo4j数据库
    """
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.database = database
            self._init_constraints()
        except ImportError:
            raise ImportError("请安装neo4j: pip install neo4j")
    
    def _init_constraints(self):
        """初始化索引和约束"""
        with self.driver.session(database=self.database) as session:
            # 创建唯一约束
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Page) REQUIRE p.page_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (a:App) REQUIRE a.app_id IS UNIQUE",
                "CREATE INDEX IF NOT EXISTS FOR (p:Page) ON (p.page_name)",
                "CREATE INDEX IF NOT EXISTS FOR (p:Page) ON (p.app_id)"
            ]
            for c in constraints:
                try:
                    session.run(c)
                except:
                    pass
    
    def add_page(self, page: Page) -> bool:
        query = """
        MERGE (p:Page {page_id: $page_id})
        SET p += $props
        """
        with self.driver.session(database=self.database) as session:
            session.run(query, page_id=page.page_id, props=page.to_dict())
        return True
    
    def add_transition(self, transition: Transition) -> bool:
        query = """
        MATCH (s:Page {page_id: $source_id})
        MATCH (t:Page {page_id: $target_id})
        MERGE (s)-[r:TRANSITIONS_TO {transition_id: $tid}]->(t)
        SET r += $props
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                source_id=transition.source_page_id,
                target_id=transition.target_page_id,
                tid=transition.transition_id,
                props=transition.to_dict()
            )
        return True
    
    def get_page(self, page_id: str) -> Optional[Page]:
        query = "MATCH (p:Page {page_id: $page_id}) RETURN p"
        with self.driver.session(database=self.database) as session:
            result = session.run(query, page_id=page_id)
            record = result.single()
            if record:
                data = dict(record["p"])
                return Page(**data)
        return None
    
    def find_shortest_path(self, start_id: str, end_id: str) -> Optional[PathResult]:
        query = """
        MATCH path = shortestPath(
            (s:Page {page_id: $start_id})-[:TRANSITIONS_TO*]->(e:Page {page_id: $end_id})
        )
        RETURN [n IN nodes(path) | n.page_id] AS pages,
               [r IN relationships(path) | properties(r)] AS transitions
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, start_id=start_id, end_id=end_id)
            record = result.single()
            if record:
                return PathResult(
                    pages=record["pages"],
                    transitions=record["transitions"],
                    total_steps=len(record["pages"]) - 1
                )
        return None
    
    def get_outgoing_transitions(self, page_id: str) -> List[Transition]:
        query = """
        MATCH (p:Page {page_id: $page_id})-[r:TRANSITIONS_TO]->(t:Page)
        RETURN properties(r) AS trans
        """
        transitions = []
        with self.driver.session(database=self.database) as session:
            result = session.run(query, page_id=page_id)
            for record in result:
                data = record["trans"]
                transitions.append(Transition(**data))
        return transitions
    
    def close(self):
        self.driver.close()


# 工厂函数
def create_graph_store(config: Dict) -> BaseGraphStore:
    """根据配置创建图存储实例"""
    store_type = config.get("type", "memory")
    
    if store_type == "memory":
        return MemoryGraphStore()
    elif store_type == "neo4j":
        return Neo4jGraphStore(
            uri=config["uri"],
            user=config["user"],
            password=config["password"],
            database=config.get("database", "neo4j")
        )
    else:
        raise ValueError(f"不支持的图存储类型: {store_type}")


# 便捷别名
GraphStore = MemoryGraphStore  # 默认使用内存存储
