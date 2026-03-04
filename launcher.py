"""智能报告系统启动器"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys

# 确保路径正确
sys.path.insert(0, os.path.abspath("."))

# 现在导入项目模块 - 绕过相对导入问题
from src.backend.database import init_db

# 直接导入路由对象（避免相对导入问题）
from src.backend.routers import (
    templates,
    instances,
    documents,
    tasks,
    chat,
    design,
    feedback,
)

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
FRONTEND_DIR = os.path.join(os.getcwd(), "src", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
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
    print("[OK] Database initialized successfully!")
    print("[INFO] Intelligent Report System is running at: http://localhost:8000")


if __name__ == "__main__":
    import uvicorn

    # 不直接启动，由外部调用
    print("App loaded. Ready to run with uvicorn.")


# 启动函数便于外部调用
def run_app():
    import uvicorn

    uvicorn.run(
        "launcher:app", host="0.0.0.0", port=8000, reload=False, log_level="info"
    )
