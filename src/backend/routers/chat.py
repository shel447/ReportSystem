"""对话交互路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ..chat_response_service import generate_chat_reply
from ..database import get_db
from ..models import ChatSession, ReportTemplate, gen_id
from ..system_settings_service import get_settings_payload
from ..template_index_service import TemplateIndexUnavailableError, match_templates

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str
    session_id: str = ""


@router.post("")
def send_message(data: ChatMessage, db: Session = Depends(get_db)):
    session = None
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.session_id == data.session_id).first()
    if not session:
        session = ChatSession(session_id=gen_id(), messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    messages = list(session.messages or [])
    messages.append({"role": "user", "content": data.message})

    reply = ""
    action = None
    gateway = OpenAICompatGateway()
    templates = db.query(ReportTemplate).count()
    settings = get_settings_payload(db)
    session.matched_template_id = None

    if templates == 0:
        reply = "当前还没有可用模板，请先在“模板管理”中创建报告模板。"
    elif not settings["is_ready"]:
        reply = "系统设置尚未完成，请先到“系统设置”中配置 Completion 与 Embedding 接口，再开始对话生成。"
    else:
        try:
            matched = match_templates(db, data.message, gateway)
            if matched["auto_match"]:
                template = db.query(ReportTemplate).filter(
                    ReportTemplate.template_id == matched["best"]["template_id"]
                ).first()
                if not template:
                    raise HTTPException(status_code=404, detail="Matched template not found")
                reply = generate_chat_reply(
                    db,
                    gateway,
                    data.message,
                    matched_template={
                        "name": template.name,
                        "scenario": template.scenario,
                        "description": template.description,
                    },
                )
                action = _build_param_form_action(template)
                session.matched_template_id = template.template_id
            else:
                reply = generate_chat_reply(db, gateway, data.message, candidates=matched["candidates"])
                action = {
                    "type": "show_template_candidates",
                    "candidates": [
                        {
                            "template_id": item["template_id"],
                            "template_name": item["template_name"],
                            "scenario": item["scenario"],
                            "score": item["score"],
                            "match_reasons": item["match_reasons"],
                        }
                        for item in matched["candidates"]
                    ],
                }
        except AIConfigurationError as exc:
            reply = str(exc)
        except TemplateIndexUnavailableError as exc:
            reply = str(exc)
        except AIRequestError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    messages.append({"role": "assistant", "content": reply, **({"action": action} if action else {})})
    session.messages = messages

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "messages")
    db.commit()

    return {
        "session_id": session.session_id,
        "reply": reply,
        "action": action,
        "matched_template_id": session.matched_template_id,
        "messages": messages,
    }


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "messages": session.messages,
        "matched_template_id": session.matched_template_id,
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "deleted"}



def _build_param_form_action(template: ReportTemplate):
    return {
        "type": "show_param_form",
        "template_id": template.template_id,
        "template_name": template.name,
        "scenario": template.scenario or "",
        "content_params": template.content_params or [],
        "outline": template.outline or [],
        "default_params": [
            {"name": "date", "label": "报告日期", "type": "date", "required": True, "default": ""},
            {
                "name": "devices",
                "label": "设备列表",
                "type": "text",
                "required": True,
                "default": "Router-001, Switch-001",
                "placeholder": "用逗号分隔多台设备",
            },
        ],
    }
