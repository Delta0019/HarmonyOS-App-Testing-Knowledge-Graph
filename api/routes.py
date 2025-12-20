"""
REST API服务

提供HTTP接口供远程调用
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
from pydantic import BaseModel

# FastAPI相关
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("提示: 安装 fastapi 和 uvicorn 以启用API服务")
    print("pip install fastapi uvicorn")

from kg_core.graph_store import MemoryGraphStore
from kg_core.vector_store import VectorStoreManager
from kg_core.embeddings import EmbeddingModel
from agent_interface.kg_client import KGClient


# ==================== 请求/响应模型 ====================

class PathQueryRequest(BaseModel):
    app_id: str
    intent: str
    current_page_id: Optional[str] = None
    max_steps: int = 10


class NextActionRequest(BaseModel):
    current_page_id: str
    intent: str
    app_id: str = ""


class PageMatchRequest(BaseModel):
    app_id: str
    ui_hierarchy: Optional[Dict] = None
    page_title: Optional[str] = None


class TransitionReportRequest(BaseModel):
    from_page: str
    action: Dict
    to_page: str
    success: bool = True
    latency_ms: int = 0


class AddPageRequest(BaseModel):
    app_id: str
    page_name: str
    page_type: str = "other"
    description: str = ""
    intents: List[str] = []


class RegisterIntentRequest(BaseModel):
    app_id: str
    intent_text: str
    target_page: Optional[str] = None
    keywords: List[str] = []


class RAGQueryRequest(BaseModel):
    app_id: str
    query: str
    current_page_id: Optional[str] = None


# ==================== API服务 ====================

def create_app() -> "FastAPI":
    """创建FastAPI应用"""
    
    if not HAS_FASTAPI:
        raise ImportError("需要安装fastapi: pip install fastapi uvicorn")
    
    app = FastAPI(
        title="HarmonyOS Knowledge Graph API",
        description="鸿蒙App自动化测试知识图谱服务",
        version="1.0.0"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 初始化KG客户端（全局单例）
    kg_client = KGClient()
    
    # ==================== 查询接口 ====================
    
    @app.post("/api/v1/query/path")
    async def query_path(request: PathQueryRequest):
        """根据意图查询操作路径"""
        result = kg_client.query_path(
            app_id=request.app_id,
            intent=request.intent,
            current_page=request.current_page_id,
            max_steps=request.max_steps
        )
        return result
    
    @app.post("/api/v1/query/next-action")
    async def get_next_action(request: NextActionRequest):
        """获取下一步推荐操作"""
        action = kg_client.get_next_action(
            current_page=request.current_page_id,
            intent=request.intent,
            app_id=request.app_id
        )
        if action:
            return {"action": action.to_dict()}
        return {"action": None}
    
    @app.post("/api/v1/query/match-page")
    async def match_page(request: PageMatchRequest):
        """匹配当前页面"""
        result = kg_client.match_current_page(
            app_id=request.app_id,
            ui_hierarchy=request.ui_hierarchy,
            page_title=request.page_title
        )
        if result:
            return result
        raise HTTPException(status_code=404, detail="未找到匹配的页面")
    
    @app.get("/api/v1/pages/{page_id}/actions")
    async def get_page_actions(page_id: str):
        """获取页面的可用操作"""
        actions = kg_client.get_available_actions(page_id)
        return {"actions": actions}
    
    # ==================== RAG接口 ====================
    
    @app.post("/api/v1/rag/retrieve")
    async def rag_retrieve(request: RAGQueryRequest):
        """RAG检索"""
        context = kg_client.get_rag_context(
            app_id=request.app_id,
            query=request.query,
            current_page=request.current_page_id
        )
        return context
    
    # ==================== 更新接口 ====================
    
    @app.post("/api/v1/graph/report-transition")
    async def report_transition(request: TransitionReportRequest):
        """上报页面转换"""
        kg_client.report_transition(
            from_page=request.from_page,
            action=request.action,
            to_page=request.to_page,
            success=request.success,
            latency_ms=request.latency_ms
        )
        return {"status": "ok"}
    
    @app.post("/api/v1/graph/add-page")
    async def add_page(request: AddPageRequest):
        """添加页面"""
        page_id = kg_client.add_page(
            app_id=request.app_id,
            page_name=request.page_name,
            page_type=request.page_type,
            description=request.description,
            intents=request.intents
        )
        return {"page_id": page_id}
    
    @app.post("/api/v1/intent/register")
    async def register_intent(request: RegisterIntentRequest):
        """注册意图"""
        intent_id = kg_client.register_intent(
            app_id=request.app_id,
            intent_text=request.intent_text,
            target_page=request.target_page,
            keywords=request.keywords
        )
        return {"intent_id": intent_id}
    
    # ==================== 管理接口 ====================
    
    @app.get("/api/v1/graph/stats")
    async def get_stats():
        """获取图谱统计"""
        return kg_client.get_graph_stats()
    
    @app.get("/api/v1/graph/export")
    async def export_graph():
        """导出图谱"""
        return kg_client.export_graph()
    
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}
    
    return app


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """运行API服务"""
    if not HAS_FASTAPI:
        print("错误: 需要安装fastapi和uvicorn")
        print("pip install fastapi uvicorn")
        return
    
    app = create_app()
    print(f"启动API服务: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
