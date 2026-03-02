"""对话交互路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import ChatSession, ReportTemplate, gen_id
from ..llm_mock import generate_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str
    session_id: str = ""


@router.post("")
def send_message(data: ChatMessage, db: Session = Depends(get_db)):
    # 获取或创建会话
    session = None
    if data.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == data.session_id).first()

    if not session:
        session = ChatSession(session_id=gen_id(), messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    # 记录用户消息
    msgs = list(session.messages or [])
    msgs.append({"role": "user", "content": data.message})

    # 尝试匹配模板
    templates = db.query(ReportTemplate).all()
    matched = None
    for t in templates:
        if t.scenario and t.scenario.lower() in data.message.lower():
            matched = t
            break
        if t.name and t.name.lower() in data.message.lower():
            matched = t
            break

    context = {"matched_template": matched.name if matched else None}
    reply = generate_chat_response(data.message, context)

    if matched and not session.matched_template_id:
        session.matched_template_id = matched.template_id
        reply = (f"已为您匹配到模板「{matched.name}」(场景: {matched.scenario})。\n\n"
                 f"请提供以下参数：\n"
                 f"1. 日期 (date)\n"
                 f"2. 设备列表 (devices)\n\n"
                 f"您可以在左侧「报告实例」页面基于此模板生成报告。")

    msgs.append({"role": "assistant", "content": reply})
    session.messages = msgs

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "messages")
    db.commit()

    return {
        "session_id": session.session_id,
        "reply": reply,
        "matched_template_id": session.matched_template_id,
        "messages": msgs,
    }


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "messages": session.messages,
        "matched_template_id": session.matched_template_id,
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "deleted"}
