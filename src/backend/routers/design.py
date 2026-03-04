from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import os
import zipfile
import io
from typing import List, Dict

router = APIRouter(tags=["Design Docs"])

DESIGN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "design")

@router.get("/design")
async def list_design_docs() -> List[Dict[str, str]]:
    """获取设计文档列表"""
    if not os.path.exists(DESIGN_DIR):
        raise HTTPException(status_code=404, detail="Design directory not found")
    
    docs = []
    for file in os.listdir(DESIGN_DIR):
        if file.endswith(".md"):
            docs.append({
                "name": file,
                "title": file.replace(".md", "").replace("_", " ").title()
            })
    return sorted(docs, key=lambda x: x["name"])

@router.get("/design/{filename}")
async def get_design_doc(filename: str):
    """获取指定设计文档内容"""
    if not filename.endswith(".md"):
        filename += ".md"
    
    file_path = os.path.join(DESIGN_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"name": filename, "content": content}

@router.get("/design/download")
async def download_design_docs():
    """打包并下载所有设计文档"""
    if not os.path.exists(DESIGN_DIR):
        raise HTTPException(status_code=404, detail="Design directory not found")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(DESIGN_DIR):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, DESIGN_DIR)
                    zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=design_docs.zip"}
    )
