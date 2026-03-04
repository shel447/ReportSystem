"""智能报告系统 - FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import init_db
from .routers import templates, instances, documents, tasks, chat, design

app = FastAPI(title="智能报告 system", version="1.2.0")

# 注册路由
API_PREFIX = "/api"
app.include_router(templates.router, prefix=API_PREFIX)
app.include_router(instances.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(design.router, prefix=API_PREFIX)

# 静态文件 - 前端
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})



@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ 数据库初始化完成")
    print("✅ 智能报告系统已启动: http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
