"""
嵌入模型模块

提供文本和图像的向量编码能力
支持:
1. SentenceTransformers (本地模型)
2. OpenAI Embeddings (API)
3. Mock模式 (用于测试)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union
import numpy as np
import hashlib


class BaseEmbeddingModel(ABC):
    """嵌入模型抽象基类"""
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """编码文本为向量"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        pass


class MockEmbeddingModel(BaseEmbeddingModel):
    """
    Mock嵌入模型
    
    用于测试，生成基于文本哈希的伪向量
    """
    
    def __init__(self, dim: int = 384):
        self._dim = dim
    
    @property
    def dimension(self) -> int:
        return self._dim
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """生成伪向量"""
        if isinstance(texts, str):
            texts = [texts]
        
        vectors = []
        for text in texts:
            # 基于文本哈希生成确定性向量
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # 扩展到目标维度
            seed = int.from_bytes(hash_bytes[:4], 'big')
            np.random.seed(seed)
            vec = np.random.randn(self._dim).astype(np.float32)
            # 归一化
            vec = vec / np.linalg.norm(vec)
            vectors.append(vec)
        
        return np.array(vectors)


class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """
    SentenceTransformers嵌入模型
    
    推荐模型:
    - paraphrase-multilingual-MiniLM-L12-v2 (多语言，384维)
    - BAAI/bge-small-zh-v1.5 (中文优化，512维)
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self._dim = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError("请安装sentence-transformers: pip install sentence-transformers")
    
    @property
    def dimension(self) -> int:
        return self._dim
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """编码文本"""
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(texts, convert_to_numpy=True)


class OpenAIEmbedding(BaseEmbeddingModel):
    """
    OpenAI嵌入模型
    
    使用text-embedding-3-small (1536维)
    """
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
            self._dim = 1536 if "3-small" in model else 3072
        except ImportError:
            raise ImportError("请安装openai: pip install openai")
    
    @property
    def dimension(self) -> int:
        return self._dim
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """调用OpenAI API编码"""
        if isinstance(texts, str):
            texts = [texts]
        
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        
        vectors = [np.array(item.embedding) for item in response.data]
        return np.array(vectors)


class EmbeddingModel:
    """
    嵌入模型统一接口
    
    自动选择可用的模型，优先级:
    1. SentenceTransformers (如果已安装)
    2. Mock模式 (始终可用)
    """
    
    def __init__(
        self, 
        model_name: str = "auto",
        dimension: int = 384,
        use_mock: bool = False
    ):
        self._model: BaseEmbeddingModel = None
        
        if use_mock:
            self._model = MockEmbeddingModel(dim=dimension)
            return
        
        # 尝试加载SentenceTransformers
        if model_name == "auto" or "sentence" in model_name.lower():
            try:
                self._model = SentenceTransformerEmbedding(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
                return
            except ImportError:
                pass
        
        # 回退到Mock
        print("⚠️ 使用Mock嵌入模型（仅用于测试）")
        self._model = MockEmbeddingModel(dim=dimension)
    
    @property
    def dimension(self) -> int:
        return self._model.dimension
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """编码文本为向量"""
        return self._model.encode(texts)
    
    def encode_single(self, text: str) -> List[float]:
        """编码单个文本，返回列表"""
        vec = self.encode(text)
        return vec[0].tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        vecs = self.encode([text1, text2])
        return float(np.dot(vecs[0], vecs[1]))


# 便捷函数
def get_embedding_model(config: dict = None) -> EmbeddingModel:
    """获取嵌入模型实例"""
    config = config or {}
    return EmbeddingModel(
        model_name=config.get("text_model", "auto"),
        dimension=config.get("text_dim", 384),
        use_mock=config.get("use_mock", False)
    )
