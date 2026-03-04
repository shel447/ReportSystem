"""智能报告系统 - FastAPI 主入口"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
import importlib.util

# 添加当前路径到系统模块搜索路径
sys.path.append(os.path.abspath("."))

from src.backend.database import init_db

# 动态导入路由
templates = importlib.import_module("src.backend.routers.templates")
instances = importlib.import_module("src.backend.routers.instances")
documents = importlib.import_module("src.backend.routers.documents")
tasks = importlib.import_module("src.backend.routers.tasks")
chat = importlib.import_module("src.backend.routers.chat")
design = importlib.import_module("src.backend.routers.design")
feedback = importlib.import_module("src.backend.routers.feedback")

app = FastAPI(title="智能报告 system", version="1.2.0")

# 注册路由
API_PREFIX = "/api"
app.include_router(templates.router, prefix=API_PREFIX)
app.include_router(instances.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(design.router, prefix=API_PREFIX)
app.include_router(feedback.router, prefix=API_PREFIX)

# 静态文件 - 前端
frontend_path = os.path.join(os.path.dirname(__file__), "src", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def index():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    else:
        return {
            "message": "Welcome to the Intelligent Report System - Frontend not found!"
        }


@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ 数据库初始化完成")
    print("✅ 智能报告系统已启动: http://localhost:8000")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
