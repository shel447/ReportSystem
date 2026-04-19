from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..infrastructure.persistence.database import get_db
from ..infrastructure.persistence.models import Feedback
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter(prefix="/feedback", tags=["Feedback"])

from datetime import datetime
import io
import zipfile
import base64

class FeedbackCreate(BaseModel):
    submitter: str
    content: str
    priority: str = "medium"
    images: List[str] = []  # Base64 strings

@router.post("/")
async def create_feedback(
    request: Request, 
    feedback: FeedbackCreate, 
    db: Session = Depends(get_db)
):
    """提交意见反馈"""
    try:
        # 自动提取客户端 IP
        client_ip = request.client.host if request.client else None
        
        new_feedback = Feedback(
            user_ip=client_ip,
            submitter=feedback.submitter,
            content=feedback.content,
            priority=feedback.priority,
            images=feedback.images
        )
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
        return {"status": "success", "feedback_id": new_feedback.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export.zip")
async def export_feedbacks(db: Session = Depends(get_db)):
    """导出所有反馈及相关图片资产资源为 ZIP 压缩包"""
    feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    
    md_content = "# 系统意见反馈汇总报告\n\n"
    md_content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    md_content += f"总计反馈: {len(feedbacks)} 条\n\n"
    md_content += "---\n\n"
    
    priority_map = {'high': '🔴 高', 'medium': '🟡 中', 'low': '🟢 低'}
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for fb in feedbacks:
            time_str = fb.created_at.strftime('%Y-%m-%d %H:%M:%S')
            md_content += f"### [{priority_map.get(fb.priority, '中')}] {fb.content[:30]}...\n\n"
            md_content += f"- **提出人**: {fb.submitter or '匿名'}\n"
            md_content += f"- **时间**: {time_str}\n"
            md_content += f"- **IP**: {fb.user_ip}\n\n"
            md_content += f"**反馈详情**:\n{fb.content}\n\n"
            
            if fb.images and len(fb.images) > 0:
                md_content += f"**附件图片**:\n\n"
                for idx, b64_str in enumerate(fb.images):
                    try:
                        # Parse data URI: data:image/png;base64,iVBOR...
                        header, encoded = b64_str.split(",", 1)
                        # Extract extension from header (e.g. image/png -> png)
                        ext = "png"
                        if "image/jpeg" in header:
                            ext = "jpg"
                        elif "image/webp" in header:
                            ext = "webp"
                        elif "image/gif" in header:
                            ext = "gif"
                            
                        image_data = base64.b64decode(encoded)
                        asset_path = f"assets/{fb.id}_{idx}.{ext}"
                        
                        # Write image to zip
                        zip_file.writestr(asset_path, image_data)
                        
                        # Add relative link to markdown
                        md_content += f"![相关截图 {idx+1}]({asset_path})\n\n"
                    except Exception as e:
                        print(f"Error decoding image {idx} for feedback {fb.id}: {e}")
                        md_content += f"> [图片解析失败]\n\n"
            
            md_content += "---\n\n"
            
        # Write the aggregated markdown file
        zip_file.writestr("feedbacks_report.md", md_content.encode("utf-8"))
        
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": 'attachment; filename="feedbacks_export.zip"'}
    )

@router.get("/")
async def list_feedbacks(db: Session = Depends(get_db)):
    """获取反馈列表"""
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()

@router.delete("/{feedback_id}")
async def delete_feedback(feedback_id: str, db: Session = Depends(get_db)):
    """删除指定的反馈意见"""
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    try:
        db.delete(fb)
        db.commit()
        return {"status": "success", "message": "Feedback deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
