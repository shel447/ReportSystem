"""Smart report system FastAPI entrypoint."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import init_db
from .routers import templates, instances, documents, tasks, chat, design, feedback

app = FastAPI(title="Smart Report System", version="1.2.0")

API_PREFIX = "/api"
app.include_router(templates.router, prefix=API_PREFIX)
app.include_router(instances.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(design.router, prefix=API_PREFIX)
app.include_router(feedback.router, prefix=API_PREFIX)

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
    print("Database initialized")
    print("Server started: http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
