from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

from .database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class User(Base):
    __tablename__ = "tbl_users"

    id = Column(String, primary_key=True)
    display_name = Column(String, default="")
    status = Column(String, default="active")
    profile_json = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime, nullable=True)


class ReportTemplate(Base):
    __tablename__ = "tbl_report_templates"

    id = Column(String, primary_key=True, default=gen_id)
    template_id = synonym("id")

    name = Column(String, nullable=False)
    description = Column(Text, default="")
    report_type = Column(String, default="daily")
    scenario = Column(String, default="")
    template_type = Column(String, default="")
    scene = Column(String, default="")
    schema_version = Column(String, default="v2.0")
    content = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String, default="system")
    version = Column(String, default="1.0")

    def __init__(self, **kwargs: Any) -> None:
        content = _as_dict(kwargs.pop("content", {}))
        for field in ("parameters", "sections", "match_keywords", "content_params", "outline", "output_formats"):
            if field in kwargs:
                content[field] = kwargs.pop(field)
        super().__init__(**kwargs)
        self.content = self._merged_content(content)

    def _merged_content(self, content: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = _as_dict(getattr(self, "content", {}))
        if content:
            merged.update(content)
        merged.setdefault("parameters", [])
        merged.setdefault("sections", [])
        merged.setdefault("match_keywords", [])
        merged.setdefault("content_params", [])
        merged.setdefault("outline", [])
        merged.setdefault("output_formats", ["md"])
        return merged

    @property
    def parameters(self) -> list[Any]:
        return _as_list(self._merged_content().get("parameters"))

    @parameters.setter
    def parameters(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["parameters"] = _as_list(value)
        self.content = content

    @property
    def sections(self) -> list[Any]:
        return _as_list(self._merged_content().get("sections"))

    @sections.setter
    def sections(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["sections"] = _as_list(value)
        self.content = content

    @property
    def match_keywords(self) -> list[Any]:
        return _as_list(self._merged_content().get("match_keywords"))

    @match_keywords.setter
    def match_keywords(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["match_keywords"] = _as_list(value)
        self.content = content

    @property
    def content_params(self) -> list[Any]:
        return _as_list(self._merged_content().get("content_params"))

    @content_params.setter
    def content_params(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["content_params"] = _as_list(value)
        self.content = content

    @property
    def outline(self) -> list[Any]:
        return _as_list(self._merged_content().get("outline"))

    @outline.setter
    def outline(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["outline"] = _as_list(value)
        self.content = content

    @property
    def output_formats(self) -> list[Any]:
        return _as_list(self._merged_content().get("output_formats"))

    @output_formats.setter
    def output_formats(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["output_formats"] = _as_list(value)
        self.content = content


class ReportInstance(Base):
    __tablename__ = "tbl_report_instances"

    id = Column(String, primary_key=True, default=gen_id)
    instance_id = synonym("id")

    template_id = Column(String, nullable=False)
    template_version = Column(String, default="1.0")
    user_id = Column(String, nullable=False)
    source_session_id = Column(String, nullable=True)
    source_message_id = Column(String, nullable=True)
    status = Column(String, default="draft")
    report_time = Column(DateTime, nullable=True)
    report_time_source = Column(String, default="")
    schema_version = Column(String, default="v2.0")
    content = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String, default="system")

    def __init__(self, **kwargs: Any) -> None:
        content = _as_dict(kwargs.pop("content", {}))
        for field in ("input_params", "outline_content"):
            if field in kwargs:
                content[field] = kwargs.pop(field)
        kwargs.setdefault("user_id", "default")
        super().__init__(**kwargs)
        self.content = self._merged_content(content)

    def _merged_content(self, content: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = _as_dict(getattr(self, "content", {}))
        if content:
            merged.update(content)
        merged.setdefault("input_params", {})
        merged.setdefault("outline_content", [])
        return merged

    @property
    def input_params(self) -> dict[str, Any]:
        return _as_dict(self._merged_content().get("input_params"))

    @input_params.setter
    def input_params(self, value: dict[str, Any]) -> None:
        content = self._merged_content()
        content["input_params"] = _as_dict(value)
        self.content = content

    @property
    def outline_content(self) -> list[Any]:
        return _as_list(self._merged_content().get("outline_content"))

    @outline_content.setter
    def outline_content(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["outline_content"] = _as_list(value)
        self.content = content


class TemplateInstance(Base):
    __tablename__ = "tbl_template_instances"

    id = Column(String, primary_key=True, default=gen_id)
    template_instance_id = synonym("id")

    template_id = Column(String, nullable=False)
    template_name = Column(String, default="")
    template_version = Column(String, default="1.0")
    session_id = Column(String, default="")
    capture_stage = Column(String, default="outline_saved")
    report_instance_id = Column(String, nullable=True, unique=True)
    schema_version = Column(String, default="v2.0")
    content = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, default="system")

    def __init__(self, **kwargs: Any) -> None:
        content = _as_dict(kwargs.pop("content", {}))
        for field in ("input_params_snapshot", "outline_snapshot", "warnings"):
            if field in kwargs:
                content[field] = kwargs.pop(field)
        super().__init__(**kwargs)
        self.content = self._merged_content(content)

    def _merged_content(self, content: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = _as_dict(getattr(self, "content", {}))
        if content:
            merged.update(content)
        merged.setdefault("input_params_snapshot", {})
        merged.setdefault("outline_snapshot", [])
        merged.setdefault("warnings", [])
        merged.setdefault("session_id", getattr(self, "session_id", "") or "")
        return merged

    @property
    def input_params_snapshot(self) -> dict[str, Any]:
        return _as_dict(self._merged_content().get("input_params_snapshot"))

    @input_params_snapshot.setter
    def input_params_snapshot(self, value: dict[str, Any]) -> None:
        content = self._merged_content()
        content["input_params_snapshot"] = _as_dict(value)
        self.content = content

    @property
    def outline_snapshot(self) -> list[Any]:
        return _as_list(self._merged_content().get("outline_snapshot"))

    @outline_snapshot.setter
    def outline_snapshot(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["outline_snapshot"] = _as_list(value)
        self.content = content

    @property
    def warnings(self) -> list[Any]:
        return _as_list(self._merged_content().get("warnings"))

    @warnings.setter
    def warnings(self, value: list[Any]) -> None:
        content = self._merged_content()
        content["warnings"] = _as_list(value)
        self.content = content


class ChatMessage(Base):
    __tablename__ = "tbl_chat_messages"

    id = Column(String, primary_key=True, default=gen_id)
    message_id = synonym("id")

    session_id = Column(String, ForeignKey("tbl_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, nullable=False, default="default")
    role = Column(String, nullable=False)
    content = Column(Text, default="")
    action = Column(JSON, nullable=True)
    meta = Column(JSON, default=dict)
    seq_no = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utc_now)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "message_id": self.id,
            "role": self.role,
            "content": self.content or "",
            "created_at": self.created_at.isoformat().replace("+00:00", "Z") if self.created_at else None,
        }
        if self.action:
            payload["action"] = self.action
        if self.meta:
            payload["meta"] = self.meta
        return payload

    @classmethod
    def from_payload(cls, session_id: str, user_id: str, seq_no: int, payload: dict[str, Any]) -> "ChatMessage":
        created_at = payload.get("created_at")
        if isinstance(created_at, str) and created_at.endswith("Z"):
            try:
                created_at_value = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at_value = _utc_now()
        else:
            created_at_value = _utc_now()
        return cls(
            id=str(payload.get("message_id") or gen_id()),
            session_id=session_id,
            user_id=user_id or "default",
            role=str(payload.get("role") or "assistant"),
            content=str(payload.get("content") or ""),
            action=payload.get("action") if isinstance(payload.get("action"), dict) else None,
            meta=_as_dict(payload.get("meta")),
            seq_no=seq_no,
            created_at=created_at_value,
        )


class ChatSession(Base):
    __tablename__ = "tbl_chat_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = synonym("id")

    user_id = Column(String, nullable=False, default="default")
    title = Column(String, default="")
    matched_template_id = Column(String, nullable=True)
    fork_meta = Column(JSON, default=dict)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    message_rows = relationship(
        "ChatMessage",
        cascade="all, delete-orphan",
        order_by="ChatMessage.seq_no",
        lazy="selectin",
    )

    def __init__(self, **kwargs: Any) -> None:
        messages = kwargs.pop("messages", None)
        super().__init__(**kwargs)
        self._transient_instance_id = kwargs.get("instance_id")
        if messages is not None:
            self.messages = messages

    @property
    def messages(self) -> list[dict[str, Any]]:
        return [row.to_payload() for row in list(self.message_rows or [])]

    @messages.setter
    def messages(self, value: list[dict[str, Any]]) -> None:
        self.message_rows = [
            ChatMessage.from_payload(
                self.id or gen_id(),
                self.user_id or "default",
                index,
                item,
            )
            for index, item in enumerate(list(value or []), start=1)
        ]


    @property
    def instance_id(self) -> str | None:
        return getattr(self, "_transient_instance_id", None)

    @instance_id.setter
    def instance_id(self, value: str | None) -> None:
        self._transient_instance_id = value


class ReportDocument(Base):
    __tablename__ = "tbl_report_documents"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = synonym("id")

    instance_id = Column(String, nullable=False)
    template_id = Column(String, default="")
    format = Column(String, default="md")
    file_path = Column(String, default="")
    file_size = Column(Integer, default=0)
    version = Column(Integer, default=1)
    status = Column(String, default="ready")
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, default="system")


class ScheduledTask(Base):
    __tablename__ = "tbl_scheduled_tasks"

    id = Column(String, primary_key=True, default=gen_id)
    task_id = synonym("id")

    user_id = Column(String, nullable=False, default="default")
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    source_instance_id = Column(String, default="")
    template_id = Column(String, default="")
    schedule_type = Column(String, default="recurring")
    cron_expression = Column(String, default="")
    timezone = Column(String, default="Asia/Shanghai")
    enabled = Column(Boolean, default=True)
    auto_generate_doc = Column(Boolean, default=True)
    time_param_name = Column(String, default="date")
    time_format = Column(String, default="%Y-%m-%d")
    use_schedule_time_as_report_time = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    total_runs = Column(Integer, default=0)
    success_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)


class ScheduledTaskExecution(Base):
    __tablename__ = "tbl_scheduled_task_executions"

    id = Column(String, primary_key=True, default=gen_id)
    execution_id = synonym("id")

    task_id = Column(String, nullable=False)
    status = Column(String, default="success")
    generated_instance_id = Column(String, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    input_params_used = Column(JSON, default=dict)


class SystemSetting(Base):
    __tablename__ = "tbl_system_settings"

    id = Column(String, primary_key=True, default="global")
    settings_id = synonym("id")

    completion_config = Column(JSON, default=dict)
    embedding_config = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TemplateSemanticIndex(Base):
    __tablename__ = "tbl_template_semantic_indices"

    id = Column(String, primary_key=True)
    template_id = synonym("id")

    semantic_text = Column(Text, default="")
    embedding_vector = Column(JSON, default=list)
    embedding_model = Column(String, default="")
    status = Column(String, default="stale")
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Feedback(Base):
    __tablename__ = "tbl_feedbacks"

    id = Column(String, primary_key=True, default=gen_id)
    feedback_id = synonym("id")

    user_ip = Column(String, nullable=True)
    submitter = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    priority = Column(String, default="medium")
    images = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
