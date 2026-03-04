from fastapi import APIRouter, HTTPException
import os
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
