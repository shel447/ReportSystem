"""系统设置路由"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.ai.openai_compat import AIConfigurationError, OpenAICompatGateway
from ..infrastructure.persistence.database import get_db
from ..infrastructure.settings.system_settings import (
    build_completion_provider_config,
    build_embedding_provider_config,
    get_settings_payload,
    save_settings,
)

router = APIRouter(prefix="/system-settings", tags=["system-settings"])


class CompletionSettingsUpdate(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    clear_api_key: bool = False
    temperature: Optional[float] = None
    timeout_sec: Optional[int] = None


class EmbeddingSettingsUpdate(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    clear_api_key: bool = False
    timeout_sec: Optional[int] = None
    use_completion_auth: Optional[bool] = None


class SettingsUpdateRequest(BaseModel):
    completion: CompletionSettingsUpdate
    embedding: EmbeddingSettingsUpdate


class SettingsTestRequest(BaseModel):
    target: Literal["completion", "embedding", "both"] = "both"


@router.get("")
def get_system_settings(db: Session = Depends(get_db)):
    payload = get_settings_payload(db)
    payload["index_status"] = get_index_status(db)
    return payload


@router.put("")
def update_system_settings(data: SettingsUpdateRequest, db: Session = Depends(get_db)):
    payload = save_settings(db, data.model_dump(exclude_unset=True))
    payload["index_status"] = get_index_status(db)
    return payload


@router.post("/test")
def test_system_settings(data: SettingsTestRequest, db: Session = Depends(get_db)):
    gateway = OpenAICompatGateway()
    result = {"target": data.target}
    if data.target in ("completion", "both"):
        result["completion"] = _test_completion(db, gateway)
    if data.target in ("embedding", "both"):
        result["embedding"] = _test_embedding(db, gateway)
    return result


@router.post("/reindex")
def rebuild_template_indices(db: Session = Depends(get_db)):
    try:
        return reindex_all_templates(db)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _test_completion(db: Session, gateway: OpenAICompatGateway):
    try:
        config = build_completion_provider_config(db)
        response = gateway.chat_completion(
            config,
            [
                {"role": "system", "content": "你是连通性测试助手。"},
                {"role": "user", "content": "请只回复：completion test ok"},
            ],
            temperature=0,
            max_tokens=32,
        )
        return {
            "ok": True,
            "model": response["model"],
            "preview": response["content"][:120],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _test_embedding(db: Session, gateway: OpenAICompatGateway):
    try:
        config = build_embedding_provider_config(db)
        vector = gateway.create_embedding(config, ["embedding test"])[0]
        return {
            "ok": True,
            "model": config.model,
            "dimension": len(vector),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _empty_index_status():
    return {
        "ready_count": 0,
        "stale_count": 0,
        "error_count": 0,
        "total_count": 0,
    }


def get_index_status(db: Session):
    _ = db
    return _empty_index_status()


def reindex_all_templates(db: Session):
    return {
        "message": "当前版本不再维护独立模板语义索引，模板匹配直接基于正式模板对象进行。",
        "index_status": get_index_status(db),
    }
