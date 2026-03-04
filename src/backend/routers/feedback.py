from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Feedback
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter(prefix="/feedback", tags=["Feedback"])

from datetime import datetime
import io

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
        client_ip = request.client.host
        
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
        return {"status": "success", "feedback_id": new_feedback.feedback_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export.md")
async def export_feedbacks(db: Session = Depends(get_db)):
    """导出所有反馈为 Markdown 文档"""
    feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    
    md_content = "# 系统意见反馈汇总报告\n\n"
    md_content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    md_content += f"总计反馈: {len(feedbacks)} 条\n\n"
    md_content += "---\n\n"
    
    priority_map = {'high': '🔴 高', 'medium': '🟡 中', 'low': '🟢 低'}
    
    for fb in feedbacks:
        time_str = fb.created_at.strftime('%Y-%m-%d %H:%M:%S')
        md_content += f"### [{priority_map.get(fb.priority, '中')}] {fb.content[:30]}...\n\n"
        md_content += f"- **提出人**: {fb.submitter or '匿名'}\n"
        md_content += f"- **时间**: {time_str}\n"
        md_content += f"- **IP**: {fb.user_ip}\n\n"
        md_content += f"**反馈详情**:\n{fb.content}\n\n"
        
        if fb.images:
            md_content += f"**附件图片**: 已附带 {len(fb.images)} 张截图 (Base64 数据略)\n\n"
        
        md_content += "---\n\n"
    
    output = io.StringIO(md_content)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="feedbacks_report.md"'}
    )

@router.get("/")
async def list_feedbacks(db: Session = Depends(get_db)):
    """获取反馈列表"""
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()
