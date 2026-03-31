# utg/graph.py
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Tuple

def _json_serializable(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return [_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    else:
        return obj

@dataclass
class EdgeStat:
    count: int = 0
    success: int = 0
    fail: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate, return 0 if no attempts."""
        if self.count == 0:
            return 0.0
        return self.success / self.count

class UTG:
    def __init__(self):
        self.nodes = {}  # state_id -> meta
        self.edges = {}  # (s1, action_key, s2) -> EdgeStat

    def add_node(self, sid, meta=None):
        if sid not in self.nodes:
            self.nodes[sid] = meta or {}

    def add_edge(self, s1, action, s2, success=None):
        # Convert action to JSON-serializable format before dumping
        action_clean = _json_serializable(action)
        akey = json.dumps(action_clean, sort_keys=True, ensure_ascii=False)
        key = (s1, akey, s2)
        st = self.edges.get(key, EdgeStat())
        st.count += 1
        if success is True: st.success += 1
        if success is False: st.fail += 1
        self.edges[key] = st
    
    def out_edges(self, state_id: str) -> List[Tuple[str, Dict[str, Any], str, EdgeStat]]:
        """
        Get all outgoing edges from a given state.
        
        Args:
            state_id: The source state ID
            
        Returns:
            List of (s1, action_dict, s2, EdgeStat) tuples
        """
        result = []
        for (s1, action_key, s2), stat in self.edges.items():
            if s1 == state_id:
                try:
                    action_dict = json.loads(action_key)
                except json.JSONDecodeError:
                    action_dict = {"raw": action_key}
                result.append((s1, action_dict, s2, stat))
        return result
    
    def save(self, path: str):
        """
        Save UTG to JSON file.
        
        Args:
            path: File path to save to
        """
        # Ensure nodes and their metadata are JSON-serializable
        serializable_nodes = {}
        for node_id, meta in self.nodes.items():
            serializable_nodes[node_id] = _json_serializable(meta)
        
        data = {
            "nodes": serializable_nodes,
            "edges": [
                {
                    "s1": s1,
                    "action_key": akey,
                    "s2": s2,
                    "count": stat.count,
                    "success": stat.success,
                    "fail": stat.fail
                }
                for (s1, akey, s2), stat in self.edges.items()
            ]
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str):
        """
        Load UTG from JSON file.
        
        Args:
            path: File path to load from
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.nodes = data.get("nodes", {})
        self.edges = {}
        
        for edge_data in data.get("edges", []):
            s1 = edge_data["s1"]
            akey = edge_data["action_key"]
            s2 = edge_data["s2"]
            stat = EdgeStat(
                count=edge_data["count"],
                success=edge_data["success"],
                fail=edge_data["fail"]
            )
            self.edges[(s1, akey, s2)] = stat
