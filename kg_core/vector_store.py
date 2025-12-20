"""
向量数据库操作模块

支持两种模式:
1. memory: 使用NumPy的内存向量存储 (用于Demo)
2. milvus: 使用Milvus向量数据库 (生产环境)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class SearchResult:
    """向量搜索结果"""
    id: str
    score: float
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "score": self.score,
            "metadata": self.metadata
        }


class BaseVectorStore(ABC):
    """向量存储抽象基类"""
    
    @abstractmethod
    def insert(self, id: str, vector: List[float], metadata: Dict = None):
        pass
    
    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5) -> List[SearchResult]:
        pass
    
    @abstractmethod
    def delete(self, id: str):
        pass


class MemoryVectorStore(BaseVectorStore):
    """
    内存向量存储
    
    使用NumPy实现简单的向量相似度搜索
    适用于Demo和小规模测试
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict] = {}
    
    def insert(self, id: str, vector: List[float], metadata: Dict = None):
        """插入向量"""
        vec = np.array(vector, dtype=np.float32)
        # 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        self.vectors[id] = vec
        self.metadata[id] = metadata or {}
    
    def batch_insert(self, items: List[Tuple[str, List[float], Dict]]):
        """批量插入"""
        for id, vector, metadata in items:
            self.insert(id, vector, metadata)
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[SearchResult]:
        """余弦相似度搜索"""
        if not self.vectors:
            return []
        
        query = np.array(query_vector, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm
        
        # 计算所有向量的余弦相似度
        scores = []
        for id, vec in self.vectors.items():
            similarity = float(np.dot(query, vec))
            scores.append((id, similarity))
        
        # 按相似度排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回top_k结果
        results = []
        for id, score in scores[:top_k]:
            results.append(SearchResult(
                id=id,
                score=score,
                metadata=self.metadata.get(id, {})
            ))
        return results
    
    def search_with_filter(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        filter_fn=None
    ) -> List[SearchResult]:
        """带过滤条件的搜索"""
        if not self.vectors:
            return []
        
        query = np.array(query_vector, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm
        
        scores = []
        for id, vec in self.vectors.items():
            # 应用过滤条件
            if filter_fn and not filter_fn(self.metadata.get(id, {})):
                continue
            similarity = float(np.dot(query, vec))
            scores.append((id, similarity))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for id, score in scores[:top_k]:
            results.append(SearchResult(
                id=id,
                score=score,
                metadata=self.metadata.get(id, {})
            ))
        return results
    
    def get(self, id: str) -> Optional[Tuple[np.ndarray, Dict]]:
        """获取向量和元数据"""
        if id in self.vectors:
            return self.vectors[id], self.metadata.get(id, {})
        return None
    
    def delete(self, id: str):
        """删除向量"""
        if id in self.vectors:
            del self.vectors[id]
        if id in self.metadata:
            del self.metadata[id]
    
    def clear(self):
        """清空存储"""
        self.vectors.clear()
        self.metadata.clear()
    
    def count(self) -> int:
        """获取向量数量"""
        return len(self.vectors)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension
        }


class MilvusVectorStore(BaseVectorStore):
    """
    Milvus向量存储
    
    生产环境使用，需要Milvus服务
    """
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 19530,
        collection_name: str = "harmonyos_kg",
        dimension: int = 384
    ):
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
            self.Collection = Collection
            self.utility = utility
        except ImportError:
            raise ImportError("请安装pymilvus: pip install pymilvus")
        
        self.collection_name = collection_name
        self.dimension = dimension
        
        # 连接Milvus
        connections.connect(host=host, port=port)
        
        # 创建或获取集合
        self._init_collection()
    
    def _init_collection(self):
        """初始化集合"""
        if self.utility.has_collection(self.collection_name):
            self.collection = self.Collection(self.collection_name)
        else:
            from pymilvus import FieldSchema, CollectionSchema, DataType
            
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            schema = CollectionSchema(fields=fields)
            self.collection = self.Collection(name=self.collection_name, schema=schema)
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index(field_name="vector", index_params=index_params)
        
        self.collection.load()
    
    def insert(self, id: str, vector: List[float], metadata: Dict = None):
        """插入向量"""
        data = [[id], [vector], [metadata or {}]]
        self.collection.insert(data)
        self.collection.flush()
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[SearchResult]:
        """向量搜索"""
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["metadata"]
        )
        
        search_results = []
        for hits in results:
            for hit in hits:
                search_results.append(SearchResult(
                    id=hit.id,
                    score=hit.score,
                    metadata=hit.entity.get("metadata", {})
                ))
        return search_results
    
    def delete(self, id: str):
        """删除向量"""
        self.collection.delete(f'id == "{id}"')


# 多集合管理器
class VectorStoreManager:
    """
    向量存储管理器
    
    管理多个向量集合:
    - pages: 页面向量
    - intents: 意图向量
    - screenshots: 截图向量
    """
    
    def __init__(self, mode: str = "memory", dimension: int = 384):
        self.mode = mode
        self.dimension = dimension
        self.stores: Dict[str, BaseVectorStore] = {}
        
        # 初始化默认集合
        self._create_store("pages")
        self._create_store("intents")
    
    def _create_store(self, name: str) -> BaseVectorStore:
        """创建向量存储"""
        if self.mode == "memory":
            store = MemoryVectorStore(dimension=self.dimension)
        else:
            store = MilvusVectorStore(collection_name=f"kg_{name}", dimension=self.dimension)
        self.stores[name] = store
        return store
    
    def get_store(self, name: str) -> BaseVectorStore:
        """获取向量存储"""
        if name not in self.stores:
            return self._create_store(name)
        return self.stores[name]
    
    # 便捷方法
    @property
    def pages(self) -> BaseVectorStore:
        return self.get_store("pages")
    
    @property
    def intents(self) -> BaseVectorStore:
        return self.get_store("intents")


# 工厂函数
def create_vector_store(config: Dict) -> VectorStoreManager:
    """根据配置创建向量存储"""
    return VectorStoreManager(
        mode=config.get("type", "memory"),
        dimension=config.get("dimension", 384)
    )


# 便捷别名
VectorStore = MemoryVectorStore
