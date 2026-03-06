from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from sqlalchemy.orm import Session

from .ai_gateway import AIConfigurationError, ProviderConfig
from .models import SystemSetting

GLOBAL_SETTINGS_ID = "global"
_DEFAULT_COMPLETION = {
    "base_url": "",
    "model": "",
    "api_key": "",
    "temperature": 0.2,
    "timeout_sec": 60,
}
_DEFAULT_EMBEDDING = {
    "base_url": "",
    "model": "",
    "api_key": "",
    "timeout_sec": 60,
    "use_completion_auth": True,
}


def get_settings_record(db: Session) -> SystemSetting | None:
    return db.query(SystemSetting).filter(SystemSetting.settings_id == GLOBAL_SETTINGS_ID).first()


def get_settings_payload(db: Session) -> Dict[str, Any]:
    row = get_settings_record(db)
    completion = _merged_completion(row.completion_config if row else {})
    embedding = _merged_embedding(row.embedding_config if row else {})
    return {
        "completion": _public_completion(completion),
        "embedding": _public_embedding(embedding),
        "is_ready": _completion_configured(completion) and _embedding_configured(completion, embedding),
    }


def save_settings(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = get_settings_record(db)
    if row is None:
        row = SystemSetting(settings_id=GLOBAL_SETTINGS_ID)
        db.add(row)

    completion = _merged_completion(row.completion_config if row else {})
    embedding = _merged_embedding(row.embedding_config if row else {})

    completion_update = payload.get("completion") or {}
    embedding_update = payload.get("embedding") or {}

    _apply_common_updates(completion, completion_update, allow_empty_base=True)
    _apply_common_updates(embedding, embedding_update, allow_empty_base=True)

    if completion_update.get("clear_api_key"):
        completion["api_key"] = ""
    elif completion_update.get("api_key") is not None:
        completion["api_key"] = str(completion_update.get("api_key") or "").strip()

    if embedding_update.get("clear_api_key"):
        embedding["api_key"] = ""
    elif embedding_update.get("api_key") is not None:
        embedding["api_key"] = str(embedding_update.get("api_key") or "").strip()

    if embedding_update.get("use_completion_auth") is not None:
        embedding["use_completion_auth"] = bool(embedding_update.get("use_completion_auth"))

    row.completion_config = completion
    row.embedding_config = embedding
    db.commit()
    db.refresh(row)
    return get_settings_payload(db)


def build_completion_provider_config(db: Session) -> ProviderConfig:
    row = get_settings_record(db)
    completion = _merged_completion(row.completion_config if row else {})
    if not _completion_configured(completion):
        raise AIConfigurationError("系统设置未完成，请先在“系统设置”中配置 Completion 接口。")
    return ProviderConfig(
        base_url=completion["base_url"],
        model=completion["model"],
        api_key=completion["api_key"],
        timeout_sec=int(completion.get("timeout_sec") or 60),
        temperature=float(completion.get("temperature") or 0.2),
    )


def build_embedding_provider_config(db: Session) -> ProviderConfig:
    row = get_settings_record(db)
    completion = _merged_completion(row.completion_config if row else {})
    embedding = _merged_embedding(row.embedding_config if row else {})
    if not _embedding_configured(completion, embedding):
        raise AIConfigurationError("系统设置未完成，请先在“系统设置”中配置 Embedding 接口。")

    use_completion_auth = bool(embedding.get("use_completion_auth", True))
    base_url = completion["base_url"] if use_completion_auth else str(embedding.get("base_url") or "").strip()
    api_key = completion["api_key"] if use_completion_auth else str(embedding.get("api_key") or "").strip()
    return ProviderConfig(
        base_url=base_url,
        model=str(embedding.get("model") or "").strip(),
        api_key=api_key,
        timeout_sec=int(embedding.get("timeout_sec") or 60),
        temperature=0.0,
    )


def _merged_completion(raw: Dict[str, Any]) -> Dict[str, Any]:
    data = deepcopy(_DEFAULT_COMPLETION)
    if isinstance(raw, dict):
        data.update(raw)
    data["base_url"] = str(data.get("base_url") or "").strip()
    data["model"] = str(data.get("model") or "").strip()
    data["api_key"] = str(data.get("api_key") or "").strip()
    data["temperature"] = float(data.get("temperature") or 0.2)
    data["timeout_sec"] = max(1, int(data.get("timeout_sec") or 60))
    return data


def _merged_embedding(raw: Dict[str, Any]) -> Dict[str, Any]:
    data = deepcopy(_DEFAULT_EMBEDDING)
    if isinstance(raw, dict):
        data.update(raw)
    data["base_url"] = str(data.get("base_url") or "").strip()
    data["model"] = str(data.get("model") or "").strip()
    data["api_key"] = str(data.get("api_key") or "").strip()
    data["timeout_sec"] = max(1, int(data.get("timeout_sec") or 60))
    data["use_completion_auth"] = bool(data.get("use_completion_auth", True))
    return data


def _public_completion(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "base_url": config["base_url"],
        "model": config["model"],
        "temperature": config["temperature"],
        "timeout_sec": config["timeout_sec"],
        "has_api_key": bool(config["api_key"]),
        "masked_api_key": _mask_secret(config["api_key"]),
        "configured": _completion_configured(config),
    }


def _public_embedding(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "base_url": config["base_url"],
        "model": config["model"],
        "timeout_sec": config["timeout_sec"],
        "use_completion_auth": bool(config.get("use_completion_auth", True)),
        "has_api_key": bool(config["api_key"]),
        "masked_api_key": _mask_secret(config["api_key"]),
        "configured": bool(config["model"]),
    }


def _apply_common_updates(target: Dict[str, Any], incoming: Dict[str, Any], *, allow_empty_base: bool) -> None:
    if incoming.get("base_url") is not None:
        value = str(incoming.get("base_url") or "").strip()
        if value or allow_empty_base:
            target["base_url"] = value
    if incoming.get("model") is not None:
        target["model"] = str(incoming.get("model") or "").strip()
    if incoming.get("temperature") is not None:
        target["temperature"] = float(incoming.get("temperature") or 0.2)
    if incoming.get("timeout_sec") is not None:
        target["timeout_sec"] = max(1, int(incoming.get("timeout_sec") or 60))


def _completion_configured(config: Dict[str, Any]) -> bool:
    return bool(config.get("base_url") and config.get("model") and config.get("api_key"))


def _embedding_configured(completion: Dict[str, Any], embedding: Dict[str, Any]) -> bool:
    if not embedding.get("model"):
        return False
    if embedding.get("use_completion_auth", True):
        return bool(completion.get("base_url") and completion.get("api_key"))
    return bool(embedding.get("base_url") and embedding.get("api_key"))


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 10:
        return secret[:2] + "***"
    return secret[:6] + "***" + secret[-4:]

