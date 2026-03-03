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

    # 构建响应
    action = None
    if matched and not session.matched_template_id:
        session.matched_template_id = matched.template_id
        reply = f"已为您匹配到模板「{matched.name}」，请在下方表单中填写参数后生成报告。"
        # 返回结构化 action，前端据此弹出表单
        action = {
            "type": "show_param_form",
            "template_id": matched.template_id,
            "template_name": matched.name,
            "scenario": matched.scenario or "",
            "content_params": matched.content_params or [],
            "default_params": [
                {"name": "date", "label": "报告日期", "type": "date",
                 "required": True, "default": ""},
                {"name": "devices", "label": "设备列表", "type": "text",
                 "required": True, "default": "Router-001, Switch-001",
                 "placeholder": "用逗号分隔多台设备"},
            ],
        }

    msgs.append({"role": "assistant", "content": reply,
                 **({"action": action} if action else {})})
    session.messages = msgs

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "messages")
    db.commit()

    return {
        "session_id": session.session_id,
        "reply": reply,
        "action": action,
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
