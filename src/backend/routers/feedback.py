from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Feedback
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter(prefix="/feedback", tags=["Feedback"])

class FeedbackCreate(BaseModel):
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

@router.get("/")
async def list_feedbacks(db: Session = Depends(get_db)):
    """获取反馈列表"""
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()
